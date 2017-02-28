'''
Classes, functions and default representations of Ξ vectors in the algebra.
'''
import collections.abc
from itertools import groupby
from .config import ALLOWED, ALLOWED_GROUPS, ALPHA_TO_GROUP, SUB_SCRIPTS


class Alpha:
    '''Unit elements in the algebra'''
    def __init__(self, index, sign=None,
                 allowed=ALLOWED, allowed_groups=ALLOWED_GROUPS):
        '''
        Handle multiple constructor methods for αs
        '''
        self.allowed = ALLOWED
        self.allowed_groups = ALLOWED_GROUPS

        if sign is None:
            if index.startswith('-'):
                index, sign = index[1:], -1
            else:
                sign = 1

        if index not in allowed and index not in allowed_groups:
            raise ValueError('Invalid α index: {}'.format(index))

        if sign not in [1, -1]:
            raise ValueError('Invalid α sign: {}'.format(sign))

        self.index = index
        self.sign = sign

    def __repr__(self):
        neg = '-' if self.sign == -1 else ''
        return '{}α{}'.format(neg, self.index)

    def __eq__(self, other):
        return (self.index == other.index) and (self.sign == other.sign)

    def __lt__(self, other):
        return self.allowed.index(self.index) < self.allowed.index(other.index)

    def __neg__(self):
        self.sign *= -1
        return self

    def __hash__(self):
        return hash((self.index, self.sign))


class Xi:
    '''A symbolic Real value'''
    def __init__(self, val, partials=None, sign=1):
        if isinstance(val, Alpha):
            val = val.index

        self.val = val
        self.sign = sign
        self.partials = partials if partials else []

    @property
    def components(self):
        return [self]

    def __eq__(self, other):
        return (self.val == other.val) and (self.partials == other.partials)

    def __lt__(self, other):
        try:
            return ALLOWED.index(self.val) < ALLOWED.index(other.val)
        except:
            return self.val < other.val

    def __repr__(self):
        sign = '+' if self.sign == 1 else '-'
        partials = (
            '∂{}'.format(''.join(SUB_SCRIPTS[i] for i in p.index))
            for p in reversed(self.partials)
        )
        if self.val in ALLOWED + ALLOWED_GROUPS:
            display_val = ''.join(SUB_SCRIPTS[i] for i in self.val)
            return '{}{}ξ{}'.format(sign, ''.join(partials), display_val)
        else:
            return '{}{}{}'.format(sign, ''.join(partials), self.val)


class XiProduct:
    '''Symbolic Xi valued products with a single sign'''
    def __init__(self, components):
        self.components = tuple(components)
        self.partials = []
        self.sign_base = 1

    @property
    def sign(self):
        s = self.sign_base
        for comp in self.components:
            s *= comp.sign
        return s

    @sign.setter
    def sign(self, val):
        self.sign_base = val

    @property
    def val(self):
        # Expressing the product values as a dotted list of indices
        return '.'.join(c.val for c in self.components)

    def __eq__(self, other):
        same_sign = (self.sign == other.sign)
        same_components = (self.components == other.components)
        return same_sign and same_components

    def __repr__(self):
        sign = '+' if self.sign == 1 else '-'
        # Stripping component signs as we have taken care of the overall
        # product sign at initialisation.
        partials = (
            '∂{}'.format(''.join(SUB_SCRIPTS[i] for i in p.index))
            for p in reversed(self.partials)
        )
        comps = ''.join(str(c)[1:] for c in self.components)
        return sign + ''.join(partials) + comps


class Pair:
    '''A Pair may be any object along with an Alpha value'''
    def __init__(self, a, x=None):
        if x is None:
            x = Xi(a)

        if isinstance(a, Alpha):
            self.alpha = a
        else:
            self.alpha = Alpha(a)

        if not isinstance(x, (Xi, XiProduct)):
            x = Xi(x)

        self.xi = x

    def __eq__(self, other):
        return (self.alpha == other.alpha) and (self.xi == other.xi)

    def __repr__(self):
        return '({}, {})'.format(self.alpha, self.xi)


class MultiVector(collections.abc.Set):
    '''A custom container type for working efficiently with multivectors'''
    _allowed_alphas = ALLOWED

    def __init__(self, components=[]):
        # Given a list of pairs, build the mulitvector by binding the ξ values
        self.components = {Alpha(a): [] for a in self._allowed_alphas}

        for comp in components:
            if isinstance(comp, (str, Alpha)):
                comp = Pair(comp)
            if not isinstance(comp, Pair):
                raise ValueError('Arguments must be Alphas, Pairs or Strings')
            try:
                self.components[comp.alpha].append(comp.xi)
            except KeyError:
                # Negative Alpha value
                alpha, xi = comp.alpha, comp.xi
                alpha.sign = 1
                xi.sign *= -1
                self.components[alpha].append(xi)

    def __repr__(self):
        comps = ['  α{}{}'.format(str(a).ljust(5), self._nice_xi(Alpha(a)))
                 for a in self._allowed_alphas if self.components[Alpha(a)]]
        return '{\n' + '\n'.join(comps) + '\n}'

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

        xis = self.components[key]
        return [Pair(key, x) for x in xis]

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
            return xi[0]
        else:
            if for_print:
                return '(' + ', '.join(str(x) for x in xi) + ')'
            else:
                return xi

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

    def collected_terms(self):
        '''Display the multivector with factorised Xi values'''
        print('{')

        sorted(self, key=lambda x: (x.alpha, x.xi.components[0]))
        g = groupby(self, lambda x: (x.alpha, x.xi.components[0]))
        alphas_seen = []

        for key, full in g:
            current_alpha = key[0]
            comps = [f.xi.components[1:] for f in full]
            s = []
            for c in comps:
                s.extend(c)
            if s:
                if current_alpha not in alphas_seen:
                    print('  {}:'.format(key[0]))
                    alphas_seen.append(current_alpha)
                print('    {}({})'.format(key[1], ''.join(str(x) for x in s)))
        print('}')


class DelMultiVector(MultiVector):
    _allowed_alphas = ALLOWED_GROUPS  # + ALLOWED
    # _allowed_alphas = '0 123 i 0jk p 0123 i0 jk'.split()
