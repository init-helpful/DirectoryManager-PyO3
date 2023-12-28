import unittest
import os
import tempfile
import dirman


class TestFile(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = tempfile.NamedTemporaryFile(
            dir=self.temp_dir, suffix=".txt", delete=False
        )
        self.file_path = self.temp_file.name
        self.file = dirman.File(self.file_path)

    def tearDown(self):
        os.remove(self.file_path)
        os.rmdir(self.temp_dir)

    def test_new(self):
        self.assertEqual(self.file.path, self.file_path)

    def test_rename(self):
        self.file.rename("new_file.txt")
        renamed_file = dirman.File(os.path.join(self.temp_dir, "new_file.txt"))
        self.assertEqual(renamed_file.name, "new_file.txt")

    def test_read(self):
        self.temp_file.write(b"test content")
        self.temp_file.flush()
        content = self.file.read()
        self.assertEqual(content, "test content")

    def test_write(self):
        self.file.write("test content", False)
        content = self.file.read()
        self.assertEqual(content, "test content\n")

    def test_get_metadata(self):
        metadata = self.file.get_metadata()
        self.assertIsInstance(metadata, dict)
        self.assertIn("last_modified", metadata)
        self.assertIn("creation_time", metadata)
        self.assertIn("is_read_only", metadata)
        self.assertIn("size", metadata)

    def test_is_read_only(self):
        is_read_only = self.file.is_read_only()
        self.assertIsInstance(is_read_only, bool)

    def test_repr(self):
        repr_value = repr(self.file)
        self.assertEqual(repr_value, self.file.name)

    def test_eq(self):
        another_file = dirman.File(self.file_path)
        self.assertTrue(self.file == another_file)


if __name__ == "__main__":
    unittest.main()
