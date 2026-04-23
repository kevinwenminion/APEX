import pymatgen.core
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from dflow.python import upload_packages

upload_packages.append(__file__)

class StructureInfo(object):
    """Analyze structure type
    Arg:
        structure: pymatgen.core.Structure object
    """
    def __init__(self, structure: pymatgen.core.Structure, **kwargs) -> None:
        analyzer = SpacegroupAnalyzer(structure, **kwargs)
        self.__space_group_symbol = analyzer.get_space_group_symbol()
        self.__space_group_number = analyzer.get_space_group_number()
        self.__point_group_symbol = analyzer.get_point_group_symbol()
        self.__crystal_system = analyzer.get_crystal_system()
        self.__lattice_type = analyzer.get_lattice_type()
        self.__num_atoms = structure.num_sites
        self.__crystal_structure = self.__indentify_crystal()
        if self.__crystal_structure == "other":
            self.__crystal_structure = self.__indentify_crystal_from_prototype(
                structure, kwargs
            )
        # standard structure
        self.orig_structure = structure
        self.primitive_structure = analyzer.find_primitive()
        self.conventional_structure = analyzer.get_conventional_standard_structure()

    def __classify_from_symmetry(self, lattice_type, space_group_symbol, num_atoms):
        if lattice_type == 'cubic':
            if num_atoms == 1 and space_group_symbol == 'Pm-3m':
                structure_type = 'sc'
            elif num_atoms == 2 and space_group_symbol == 'Im-3m':
                structure_type = 'bcc'
            elif num_atoms == 4 and space_group_symbol == 'Fm-3m':
                structure_type = 'fcc'
            elif num_atoms == 8 and space_group_symbol == 'Fd-3m':
                structure_type = 'diamond'
            else:
                structure_type = 'other'

        elif lattice_type == 'hexagonal':
            if num_atoms == 2 and space_group_symbol == 'P6_3/mmc':
                structure_type = 'hcp'
            elif space_group_symbol == 'P6/mmm':
                structure_type = 'c32'
            else:
                structure_type = 'other'
        else:
            structure_type = 'other'

        return structure_type

    def __indentify_crystal(self) -> str:
        return self.__classify_from_symmetry(
            self.__lattice_type, self.__space_group_symbol, self.__num_atoms
        )

    def __indentify_crystal_from_prototype(self, structure, kwargs) -> str:
        # Replace all species with one element and infer the parent lattice prototype.
        # This helps classify alloy/disordered supercells whose chemistry breaks symmetry.
        prototype = pymatgen.core.Structure(
            lattice=structure.lattice,
            species=['H'] * structure.num_sites,
            coords=structure.frac_coords,
            coords_are_cartesian=False,
            site_properties=structure.site_properties,
        )

        prototype_kwargs = dict(kwargs)
        symprec = prototype_kwargs.get('symprec', 1e-3)
        angle_tolerance = prototype_kwargs.get('angle_tolerance', 5)
        if symprec is None:
            symprec = 1e-3
        if angle_tolerance is None:
            angle_tolerance = 5
        prototype_kwargs['symprec'] = max(float(symprec), 0.1)
        prototype_kwargs['angle_tolerance'] = max(float(angle_tolerance), 5)

        analyzer = SpacegroupAnalyzer(prototype, **prototype_kwargs)
        lattice_type = analyzer.get_lattice_type()
        space_group_symbol = analyzer.get_space_group_symbol()
        num_atoms = analyzer.get_conventional_standard_structure().num_sites
        return self.__classify_from_symmetry(
            lattice_type,
            space_group_symbol,
            num_atoms,
        )

    @property
    def space_group_symbol(self):
        return self.__space_group_symbol

    @property
    def space_group_number(self):
        return self.__space_group_number

    @property
    def point_group_symbol(self):
        return self.__point_group_symbol

    @property
    def crystal_system(self):
        return self.__crystal_system

    @property
    def lattice_type(self):
        return self.__lattice_type

    @property
    def num_atoms(self):
        return self.__num_atoms

    @property
    def lattice_structure(self):
        return self.__crystal_structure
