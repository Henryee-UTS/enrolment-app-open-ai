"""Offline RAG regression checks using an isolated corpus and vector store."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rag-server'))
import rag_pipeline as rag


class RAGTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.patches = [patch.object(rag, key, value) for key, value in {
            'CORPUS_PATH': root / 'corpus.jsonl',
            'AUDIT_PATH': root / 'audit.jsonl',
            'CHROMA_PATH': root / 'chroma',
            '_collection': None,
            '_last_corpus_chunks': [],
        }.items()]
        for p in self.patches:
            p.start()
        self.chunks = [
            {'chunk_id': 'count', 'text': 'Student count is 10.'},
            {'chunk_id': 'one', 'text': 'Student record: student_id=1, student_name=John, subject_code=ASD101.'},
            {'chunk_id': 'two', 'text': 'Student record: student_id=2, student_name=Sarah, subject_code=ASD101.'},
            {'chunk_id': 'three', 'text': 'Student record: student_id=3, student_name=Alex, subject_code=DB202.'},
        ]
        for c in self.chunks:
            c.update(source_id='fixture', authority_tier='tier_1', indexed_at=rag.now_iso())
        with patch.object(rag, 'build_corpus', return_value=self.chunks):
            result = rag.refresh_corpus()
        self.assertEqual(result['vector_store_status'], 'ready')

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.temp.cleanup()

    def test_count_uses_aggregate_not_top_k(self):
        answer = rag.answer_question('student count', 1)
        self.assertIn('10 students', answer['answer'])
        self.assertTrue(answer['citations'])

    def test_subject_filters_other_subjects(self):
        result = rag.answer_question('Which students are enrolled in ASD101?', 5)
        self.assertIn('John', result['answer'])
        self.assertIn('Sarah', result['answer'])
        self.assertNotIn('Alex', result['answer'])

    def test_absent_subject_abstains(self):
        result = rag.answer_question('Which students are enrolled in XYZ999?', 5)
        self.assertEqual(result['answer'], 'Insufficient evidence.')
        self.assertEqual(result['citations'], [])
        self.assertEqual(result['confidence_category'], 'Unknown')

    def test_invalid_inputs_and_audit(self):
        for query, k in [('', 5), ('student', 0), ('student', True), ('student', 21)]:
            self.assertEqual(rag.retrieve_context(query, k)['status'], 'error')
        records = [json.loads(line) for line in rag.AUDIT_PATH.read_text().splitlines()]
        self.assertEqual(sum(r['validation_status'] == 'fail' for r in records), 4)

    def test_persistent_store_and_fallback(self):
        rag._collection = None
        rag._last_corpus_chunks = []
        self.assertEqual(rag.retrieve_context('student count', 1)['results'][0]['chunk_id'], 'count')
        with patch.object(rag, 'get_collection', side_effect=RuntimeError('offline')):
            result = rag.retrieve_context('student count', 1)
        self.assertEqual(result['retrieval_mode'], 'lexical_fallback')
        self.assertEqual(result['results'][0]['chunk_id'], 'count')

    def test_empty_index_auto_refresh_uses_new_collection(self):
        rag.reset_collection()
        with patch.object(rag, "build_corpus", return_value=self.chunks):
            result = rag.retrieve_context("student count", 1)
        self.assertEqual(result["retrieval_mode"], "vector")
        self.assertEqual(result["results"][0]["chunk_id"], "count")

    def test_model_failure_is_not_success(self):
        with patch.object(rag, 'generate_with_ollama', side_effect=RuntimeError('offline')):
            result = rag.answer_question('Explain student records')
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['citations'], [])


if __name__ == '__main__':
    unittest.main()
