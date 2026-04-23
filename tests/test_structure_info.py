import os
import sys
import unittest

from pymatgen.core import Lattice, Structure

from apex.core.structure import StructureInfo

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestStructureInfo(unittest.TestCase):
    def test_identify_bcc_from_decorated_supercell(self):
        bcc = Structure(
            Lattice.cubic(3.2),
            ["Mo", "Mo"],
            [[0, 0, 0], [0.5, 0.5, 0.5]],
        )
        bcc.make_supercell([2, 2, 2])

        species = [
            "Mo",
            "Cr",
            "Mn",
            "Fe",
            "Co",
            "Ni",
            "Al",
            "Ti",
            "Mo",
            "Cr",
            "Mn",
            "Fe",
            "Co",
            "Ni",
            "Al",
            "Ti",
        ]
        for index, specie in enumerate(species):
            bcc[index] = specie

        st = StructureInfo(bcc)
        self.assertEqual(st.lattice_structure, "bcc")


if __name__ == "__main__":
    unittest.main()
