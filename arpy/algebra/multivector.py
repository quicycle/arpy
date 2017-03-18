'''
arpy (Absolute Relativity in Python)
Copyright (C) 2016-2017 Innes D. Anderson-Morrison All rights reserved.

NOTE:: To avoid cyclic imports, the __invert__ method on multivectors (which
       returns the Hermitian conjugate) is written in the arpy __init__ file!
       (I am fully aware of how horrible this is...)
'''
import collections.abc
from copy import deepcopy
from itertools import groupby
from .ar_types import Alpha, Pair, Xi
from .del_grouping import del_grouped
from .config import ALLOWED, ALLOWED_GROUPS, ALPHA_TO_GROUP, BXYZ_LIKE, \
    XI_GROUPS


class MultiVector(collections.abc.Set):
    '''A custom container type for working efficiently with multivectors'''
    _allowed_alphas = ALLOWED

    def __init__(self, components=[]):
        # Given a list of pairs, build the mulitvector by binding the ξ values
        self.components = {Alpha(a): [] for a in self._allowed_alphas}

        if isinstance(components, str):  # Allow for single string input
            components = components.split()

        for comp in components:
            if isinstance(comp, (str, Alpha)):
                comp = Pair(comp)
            if not isinstance(comp, Pair):
                raise ValueError('Arguments must be Alphas, Pairs or Strings')

            if comp.alpha.index in self._allowed_alphas:
                _comp = deepcopy(comp)
                try:
                    self.components[_comp.alpha].append(_comp.xi)
                except KeyError:
                    # Negative Alpha value
                    alpha, xi = _comp.alpha, _comp.xi
                    alpha.sign = 1
                    xi.sign *= -1
                    self.components[alpha].append(xi)

    def __repr__(self):
        comps = ['  α{}{}'.format(str(a).ljust(5), self._nice_xi(Alpha(a)))
                 for a in self._allowed_alphas if self.components[Alpha(a)]]
        return '{\n' + '\n'.join(comps) + '\n}'

    def show(self, ordering):
        '''Print the components of the MultiVector in a specified ordering'''
        if isinstance(ordering, str):
            ordering = ordering.split()

        if not all([o in self._allowed_alphas for o in ordering]):
            raise ValueError('Invalid index in ordering')

        comps = ['  α{}{}'.format(str(a).ljust(5), self._nice_xi(Alpha(a)))
                 for a in ordering if self.components[Alpha(a)]]
        print('{\n' + '\n'.join(comps) + '\n}')

    def __len__(self):
        # All allowed values are initialised with [] so we are
        # only counting componets that have a Xi value set.
        return len([v for v in self.components.values() if v != []])

    def __add__(self, other):
        # Allow for the addition of Multivectors and Pairs.
        # This will always return a new MultiVector.
        if not isinstance(other, (Pair, MultiVector)):
            raise TypeError()

        comps = [p for p in self]
        if isinstance(other, Pair):
            comps.append(other)
        elif isinstance(other, MultiVector):
            comps.extend(p for p in other)

        return MultiVector(comps)

    def __eq__(self, other):
        for alpha in self.components:
            if self.components[alpha] != other.components[alpha]:
                return False
        return True

    def __neg__(self):
        # -mvec to negate all Xis
        negated = deepcopy(self)
        for xis in negated.components.values():
            for xi in xis:
                xi.sign *= -1
        return negated

    def __contains__(self, other):
        if isinstance(other, Alpha):
            return self.components[other] != []
        elif isinstance(other, Pair):
            return other.xi in self.components[other.alpha]
        else:
            return False

    def __getitem__(self, key):
        if isinstance(key, str):
            # Allow retreval by string as well as Alpha
            key = Alpha(key)
        if not isinstance(key, Alpha):
            raise KeyError
        return [Pair(key, xi) for xi in self.components[key]]

    def __delitem__(self, key):
        if isinstance(key, str):
            key = Alpha(key)
        if not isinstance(key, Alpha):
            raise KeyError

        self.components[key] = []

    def __iter__(self):
        for alpha in self._allowed_alphas:
            try:
                for xi in self.components[Alpha(alpha)]:
                    yield Pair(alpha, xi)
            except KeyError:
                pass

    def _nice_xi(self, alpha, raise_key_error=False, for_print=True):
        '''Single element xi lists return their value raw'''
        try:
            xi = self.components[alpha]
        except KeyError:
            if raise_key_error:
                raise KeyError
        if len(xi) == 1:
            return '( ' + str(xi[0]) + ' )'
        else:
            if for_print:
                return '( ' + ', '.join(str(x) for x in xi) + ' )'
            else:
                return xi

    def copy(self):
        '''Return a copy of this multivector'''
        return deepcopy(self)

    def BTAE_grouped(self):
        '''
        Print an BTAE grouped representation of the MultiVector
        NOTE:: This deliberately does not return a new MultiVector as we
               should always be working with strict alpha values not grouped.
        '''
        by_alpha = groupby(self, key=lambda x: ALPHA_TO_GROUP[x.alpha.index])
        BTAE = [
            (group, tuple(c.xi for c in components))
            for (group, components) in by_alpha
        ]
        print('{')
        for group, comps in BTAE:
            print('  α{}'.format(group).ljust(7), comps)
        print('}')

    def del_notation(self):
        '''
        Print a del grouped version of the multivector
        '''
        print(DelMultiVector(self))

    def simplified(self, ix=0, bxyz=False, sign=False):
        '''
        Display the multivector with simplified Xi values.
        '''
        def key(x):
            return x.alpha.index

        ix2 = 1 if ix == 0 else 1
        alpha_grouped = groupby(sorted(self, key=key), key)
        seen = []

        try:
            print('{')
            for _, full in alpha_grouped:
                full = sorted(full, key=lambda x: x.xi.components[ix])
                xi_grouped = groupby(full,  key=lambda x: x.xi.components[ix])
                for common_xi, comps in xi_grouped:
                    comps = [
                        Pair(c.alpha, c.xi.components[ix2])
                        for c in comps
                    ]
                    comps = sorted(comps, key=key)
                    for component in comps:
                        if component.alpha.sign == -1:
                            component.alpha.sign = 1
                            component.xi.sign *= -1

                    if comps[0].alpha not in seen:
                        print('  {}:'.format(comps[0].alpha))
                        seen.append(comps[0].alpha)

                    if bxyz:
                        x = str(BXYZ_LIKE[common_xi.val]).ljust(3)
                        if sign:
                            signs = [c.xi.bxyz()[0] for c in comps]
                            blocks = ['■' if s == '-' else '□' for s in signs]
                            comp_str = ' '.join(blocks)
                        else:
                            comp_str = ', '.join([c.xi.bxyz() for c in comps])
                    else:
                        x = str(common_xi).ljust(6)
                        comp_str = ', '.join([str(c.xi) for c in comps])
                    print('    {}( {} )'.format(x, comp_str))
            print('}')
        except:
            print('Unable to simplify MultiVector Xi values')

    def relabel(self, index, replacement):
        '''
        Manually relabel the components of a multivector.
        This is intended for simplifying results following manual analysis.
        '''
        new_mvec = deepcopy(self)

        if index.startswith('-'):
            index = index[1:]
            xi_sign = -1
        else:
            xi_sign = 1

        if replacement.startswith('-'):
            replacement = replacement[1:]
            xi_sign *= -1

        if index in ALLOWED:
            new_xi = Xi(replacement, sign=xi_sign)
            new_mvec.components[Alpha(index)] = [new_xi]
        else:
            try:
                indices = zip(['₁', '₂', '₃'], XI_GROUPS[index])
                for comp, index in indices:
                    new_xi = Xi(replacement + comp, sign=xi_sign)
                    new_mvec.components[Alpha(index)] = [new_xi]
            except KeyError:
                raise ValueError('{} is not a valid index'.format(index))
        return new_mvec

    def relabel_many(self, pairs):
        '''Relabel each case in pairs: (index, replacement)'''
        new_mvec = deepcopy(self)
        for index, replacement in pairs:
            new_mvec = new_mvec.relabel(index, replacement)
        return new_mvec

    @property
    def v(self):
        self.del_notation()

    @property
    def s(self, ix=0, bxyz=False, sign=False):
        self.simplified(ix, bxyz, sign)


class DelMultiVector(MultiVector):
    _allowed_alphas = ALLOWED_GROUPS  # + ALLOWED
    # _allowed_alphas = '0 123 i 0jk p 0123 i0 jk'.split()

    def __init__(self, components=[]):
        # Given a list of pairs, build the mulitvector by binding the ξ values
        self.components = {Alpha(a): [] for a in self._allowed_alphas}

        for comp in del_grouped(components):
            if isinstance(comp, (str, Alpha)):
                comp = Pair(comp)
            if not isinstance(comp, Pair):
                raise ValueError('Arguments must be Alphas, Pairs or Strings')
            if comp.alpha.index in self._allowed_alphas:
                try:
                    self.components[comp.alpha].append(comp.xi)
                except KeyError:
                    # Negative Alpha value
                    alpha, xi = comp.alpha, comp.xi
                    alpha.sign = 1
                    xi.sign *= -1
                    self.components[alpha].append(xi)
