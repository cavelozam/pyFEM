#!/usr/bin/oython3.6
from pyFEM.primitives import *
from pyFEM.classtools import Collection


class Materials(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label, modulus_elasticity, modulus_elasticity_shear):
        material = Material(label, modulus_elasticity, modulus_elasticity_shear)
        Collection.add(self, material)

        return material


class Sections(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label, material, area, inertia_y, inertia_z, torsion_constant):
        section = Section(label, self.parent.materials[material], area, inertia_y, inertia_z, torsion_constant)
        Collection.add(self, section)

        return section


class Nodes(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label, x, y, z):
        node = Node(label, x, y, z)
        Collection.add(self, node)

        return node


class Trusses(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label, node_i, node_j, section):
        truss = Truss(label, self.parent.nodes[node_i], self.parent.nodes[node_j], self.parent.sections[section])
        Collection.add(self, truss)

        return truss


class Frames(Trusses):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label, node_i, node_j, section):
        frame = Frame(label, self.parent.nodes[node_i], self.parent.nodes[node_j], self.parent.sections[section])
        Collection.add(self, frame)

        return frame


class Supports(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, node, ux, uy, uz, rx, ry, rz):
        support = Support(self.parent.nodes[node], ux, uy, uz, rx, ry, rz)
        Collection.add(self, support)

        return support


class LoadPatterns(Collection):
    def __init__(self, parent):
        Collection.__init__(self)
        self.parent = parent

    def add(self, label):
        load_pattern = LoadPattern(label, self.parent)
        Collection.add(self, load_pattern)

        return load_pattern


class Structure:
    number_degrees_freedom_per_node = 6
    number_dimensions = 3

    def __init__(self):
        self.materials = Materials(self)
        self.sections = Sections(self)

        self.nodes = Nodes(self)

        self.trusses = Trusses(self)
        self.frames = Frames(self)

        self.supports = Supports(self)

        self.load_patterns = LoadPatterns(self)

    def set_degrees_freedom(self):
        for i, _node in enumerate(self.nodes):
            _node.set_degrees_freedom(np.arange(self.number_degrees_freedom_per_node * i,
                                                self.number_degrees_freedom_per_node * (i + 1)))

    def get_k(self):
        k = np.zeros(2 * (self.number_degrees_freedom_per_node * len(self.nodes),))

        for truss in self.trusses:
            degrees_freedom = np.append(truss.node_i.degrees_freedom,
                                        truss.node_j.degrees_freedom)

            for i, row in enumerate(truss.get_global_stiff_matrix()):
                for j, item in enumerate(row):
                    k[degrees_freedom[i], degrees_freedom[j]] += item

        for frame in self.frames:
            degrees_freedom = np.append(frame.node_i.degrees_freedom,
                                        frame.node_j.degrees_freedom)

            for i, row in enumerate(frame.get_global_stiff_matrix()):
                for j, item in enumerate(row):
                    k[degrees_freedom[i], degrees_freedom[j]] += item

        return k

    def solve(self):
        self.set_degrees_freedom()  # Cambiar !!!

        k = self.get_k()
        k_support = np.copy(k)

        for support in self.supports:
            degrees_freedom = support.node.degrees_freedom

            for i, item in enumerate(support.restrains):
                if item:
                    k_support[degrees_freedom[i]] = np.zeros(np.shape(k)[0])
                    k_support[:, degrees_freedom[i]] = np.zeros(np.shape(k)[0])
                    k_support[degrees_freedom[i], degrees_freedom[i]] = 1

        for load_pattern in self.load_patterns:
            f = load_pattern.get_f()

            for support in self.supports:
                degrees_freedom = support.node.degrees_freedom

                for i, item in enumerate(support.restrains):
                    if item:
                        f[degrees_freedom[i], 0] = 0

            u = np.linalg.solve(k_support, f)
            f = np.dot(k, u) - f

            for node in self.nodes:
                degrees_freedom = node.degrees_freedom
                node.displacements.add(load_pattern, *u[[degree_freedom for degree_freedom in degrees_freedom], 0])

            for support in self.supports:
                degrees_freedom = [degree_freedom for i, degree_freedom in enumerate(support.node.degrees_freedom)
                                   if support.restrains[i]]
                support.reactions.add(load_pattern, f[[degree_freedom for degree_freedom in degrees_freedom], 0])

    def __repr__(self):
        return self.__class__.__name__


if __name__ == '__main__':
    def example_1():
        """Solution to problem 7.1 from 'Microcomputadores en Ingeniería Estructural'"""
        # structure
        structure = Structure()

        # add material
        structure.materials.add("material1", 2040e4)

        # add sections
        structure.sections.add("section1", "material1", 30e-4)
        structure.sections.add("section2", "material1", 40e-4)
        structure.sections.add("section3", "material1", 100e-4)
        structure.sections.add("section4", "material1", 150e-4)

        # add nodes
        structure.nodes.add('1', 0, 0, 0)
        structure.nodes.add('2', 8, 0, 0)
        structure.nodes.add('3', 4, 3, 0)
        structure.nodes.add('4', 4, 0, 0)

        # add trusses
        structure.trusses.add('1-3', '1', '3', "section3")
        structure.trusses.add('1-4', '1', '4', "section2")
        structure.trusses.add('3-2', '3', '2', "section4")
        structure.trusses.add('4-2', '4', '2', "section2")
        structure.trusses.add('4-3', '4', '3', "section1")

        # add support
        structure.supports.add('1', True, True, True)
        structure.supports.add('2', False, True, True)
        structure.supports.add('3', False, False, True)
        structure.supports.add('4', False, False, True)

        # add load pattern
        structure.load_patterns.add("point loads")

        # add point loads
        structure.load_patterns["point loads"].point_loads.add('4', 0, -20, 0)
        structure.load_patterns["point loads"].point_loads.add('3', 5 * 0.8, 5 * 0.6, 0)

        # solve the problem
        structure.solve()

        for node in structure.nodes:
            print("node {}".format(node.label))
            for displacement in node.displacements:
                print(displacement)

        print()

        for support in structure.supports:
            print("support {}".format(support.label))
            for reaction in support.reactions:
                print(reaction)

        print()

        for truss in structure.trusses:
            print("truss {}".format(truss.label))
            for load_pattern in structure.load_patterns:
                print("load pattern: {}".format(load_pattern.label))
                print(truss.get_forces(load_pattern.label))

    def example_2():
        """Solution to problem 7.2 from 'Micromputadores en Ingeniería Estructural'"""
        # structure
        structure = Structure()

        # add material
        structure.materials.add("2100 t/cm2", 2100e4)

        # add sections
        structure.sections.add("10 cm2", "2100 t/cm2", 10e-4)
        structure.sections.add("20 cm2", "2100 t/cm2", 20e-4)
        structure.sections.add("40 cm2", "2100 t/cm2", 40e-4)
        structure.sections.add("50 cm2", "2100 t/cm2", 50e-4)

        # add nodes
        structure.nodes.add('1', 2.25, 6, 4.8)
        structure.nodes.add('2', 3.75, 6, 2.4)
        structure.nodes.add('3', 5.25, 6, 4.8)
        structure.nodes.add('4', 0.00, 0, 6.0)
        structure.nodes.add('5', 3.75, 0, 0.0)
        structure.nodes.add('6', 7.50, 0, 6.0)

        # add trusses
        structure.trusses.add('1-2', '1', '2', '20 cm2')
        structure.trusses.add('1-3', '1', '3', '20 cm2')
        structure.trusses.add('1-4', '1', '4', '40 cm2')
        structure.trusses.add('1-6', '1', '6', '50 cm2')
        structure.trusses.add('2-3', '2', '3', '20 cm2')
        structure.trusses.add('2-4', '2', '4', '50 cm2')
        structure.trusses.add('2-5', '2', '5', '40 cm2')
        structure.trusses.add('3-5', '3', '5', '50 cm2')
        structure.trusses.add('3-6', '3', '6', '40 cm2')
        structure.trusses.add('4-5', '4', '5', '10 cm2')
        structure.trusses.add('4-6', '4', '6', '10 cm2')
        structure.trusses.add('5-6', '5', '6', '10 cm2')

        # add supports
        structure.supports.add('4', True, True, True)
        structure.supports.add('5', True, True, True)
        structure.supports.add('6', True, True, True)

        # add load pattern
        structure.load_patterns.add("point loads")

        # add point loads
        structure.load_patterns["point loads"].point_loads.add('1', 10, 15, -12)
        structure.load_patterns["point loads"].point_loads.add('2',  5, -3, -10)
        structure.load_patterns["point loads"].point_loads.add('3', -4, -2,  -6)

        # solve
        structure.solve()

        for node in structure.nodes:
            print("node {}".format(node.label))
            for displacement in node.displacements:
                print(displacement)

        print()

        for support in structure.supports:
            print("support {}".format(support.label))
            for reaction in support.reactions:
                print(reaction)

        print()

        for truss in structure.trusses:
            print("truss {}".format(truss.label))
            for load_pattern in structure.load_patterns:
                print("load pattern: {}".format(load_pattern.label))
                print(truss.get_forces(load_pattern.label))

    def example_3():
        """"Solution to problem 7.6 from 'Microcomputadores en Ingeniería Estructural'"""
        # structure
        structure = Structure()

        # add material
        structure.materials.add('material1', 220e4, 85e4)

        # add sections
        structure.sections.add('section1', 'material1', 0.12, 9e-4, 1.6e-3, 1.944e-3)
        structure.sections.add('section2', 'material1', 0.10, 1.333e-3, 5.208e-4, 1.2734e-3)

        # add nodes
        structure.nodes.add('1', 0, 3, 3)
        structure.nodes.add('2', 5, 3, 3)
        structure.nodes.add('3', 0, 0, 3)
        structure.nodes.add('4', 0, 3, 0)

        # add frames
        structure.frames.add('1-2', '1', '2', 'section1')
        structure.frames.add('3-1', '3', '1', 'section1')
        structure.frames.add('4-1', '4', '1', 'section2')

        # add supports
        structure.supports.add('2', *6 * (True,))
        structure.supports.add('3', *6 * (True,))
        structure.supports.add('4', *6 * (True,))

        # add load pattern
        structure.load_patterns.add("distributed loads")

        # add distributed loads
        structure.load_patterns["distributed loads"].distributed_loads.add('1-2', 0, -2.4, 0)
        structure.load_patterns["distributed loads"].distributed_loads.add('4-1', 0, -3.5, 0)

        # solve
        structure.solve()

        np.set_printoptions(precision=3)
        for node in structure.nodes:
            print(node.label, node.displacements["distributed loads"].displacement)
            # print("node {}".format(node.label))
            # for displacement in node.displacements:
            #     print(displacement)

        # print()
        #
        # for support in structure.supports:
        #     print("support {}".format(support.label))
        #     for reacttion in support.reactions:
        #         print(reacttion)
        #
        # print()


    # example_1()
    # example_2()
    example_3()
