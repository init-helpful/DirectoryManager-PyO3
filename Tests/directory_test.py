import unittest
import dirman

class TestDirectory(unittest.TestCase):
  def setUp(self):
      self.directory = dirman.Directory('/path/to/your/directory')

  def test_new(self):
      self.assertEqual(self.directory.path, '/path/to/your/directory')

if __name__ == '__main__':
  unittest.main()
