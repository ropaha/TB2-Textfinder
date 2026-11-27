import unittest

from tb2.muster import historical_resource_document, extract_counter_lines


class Resource613Tests(unittest.TestCase):
    def sample(self):
        data = bytearray(545 + 3 * 613)
        data[:4] = bytes.fromhex("5408cdab")
        data[544] = 3
        for i, ext in enumerate(("STN", "ORN", "BAU")):
            p = 545 + i * 613
            path = ("C:\\STEIN\\SIGNUM\\" + ext + "\\TEST." + ext).encode("ascii")
            data[p + 40] = i + 1
            data[p + 53] = (0, 2, 32)[i]
            data[p + 54] = 2
            data[p + 57] = len(path)
            data[p + 58:p + 58 + len(path)] = path
        return data

    def test_valid(self):
        data = bytes(self.sample())
        self.assertEqual(historical_resource_document(data), ("STN", "ORN", "BAU"))
        self.assertEqual(extract_counter_lines(data), ([], []))

    def test_invalid(self):
        original = self.sample()
        for offset, value in ((0, 0), (544, 2), (585, 9), (586, 1),
                              (599, 9), (602, 0), (603, 0)):
            with self.subTest(offset=offset):
                data = original.copy()
                data[offset] = value
                self.assertIsNone(historical_resource_document(bytes(data)))
        self.assertIsNone(historical_resource_document(bytes(original[:-1])))
        self.assertIsNone(historical_resource_document(bytes(original) + b"\x00"))
