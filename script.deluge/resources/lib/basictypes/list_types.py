"""Restricted lists with base-datatype meta-type support

This module is normally used to easily create a baseType
definition for a property like so:

	listof_Blarghs = list_types.listof(
		name = "listof_Blarghs",
		baseType = Blargh,
		dataType = "list.Blargh",
	)
	class X(propertied.Propertied):
		blarghs = common.ListProperty(
			'blarghs', "A sequence of Blarghs",
			baseType = listof_Blarghs,
		)

The listof_Blarghs type (a sub-class of list) will
have coercion, data-type checking, and factories support,
and a dataType attribute which allows the wxoo system
to service instances in a number of useful ways.

The module also includes a set of "basic" list-of-types
mirroring those in the basic_types module.
"""
import inspect
import os
import types

from basictypes import basic_types, rlist, latebind


class ListOf(rlist.rlist):
    """List of a particular object-type

    This is the default base class for the classes
    generated by the listof meta-class.  It is a
    simple restrictive list (see the superclass)
    which calls its class'es coerce_single method
    on every value added.
    """

    def beforeAdd(self, value):
        """Called before all attempts to add an item"""
        return type(self).coerce_single(value)


class listof(type):
    """Meta-class which creates a new typed list-class

    The listof meta-class is normally called like so:

        classname = listof(
            "classname",
            baseType,
            dataType = "list.something",
        )

    with baseType being the basictypes specifier for the
    base object type, or a simple data-class.

    Note: there is a horrible hack that tries to figure
    out the correct __module__ name for the resulting class,
    this is very annoyingly set to list_types by default,
    rather than the module which calls listof() :( .
    """

    def __new__(cls, baseType, name="", bases=(ListOf,), **named):
        if named.has_key('dataType'):
            dataType = named.get('dataType')
        elif hasattr(baseType, 'dataType'):
            dataType = baseType.dataType
        elif hasattr(baseType, '__name__'):
            dataType = baseType.__name__
        elif isinstance(baseType, str):
            # probably a string-specified data-type
            dataType = (baseType.split('.')[-1])
        else:
            raise ValueError("""listof couldn't determine dataType specifier for %r"""%(baseType))
        if not name:
            name = "list_%s"%(dataType.replace(".", '_'))
        if not named.has_key('dataType'):
            # we're auto-calculating a data-type, add list. to the front
            dataType = 'list.' + dataType + 's'
        named["dataType"] = dataType
        baseObject = super(listof, cls).__new__(cls, name, bases, {})
        baseObject.baseType = baseType
        ## Following is the code to try and figure out the
        ## module in which the class should reside, this is
        ## fragile, as there might be some code that doesn't
        ## setup the class in the root of the module.  Like
        ## any other class, that class will be unpickle-able.
        stack = inspect.stack(1)
        module = stack[1][0].f_globals['__name__']
        baseObject.__module__ = module
        from basicproperty import linearise
        linearise.Lineariser.registerHelper(baseObject, linearise.SequenceLin())
        return baseObject

    def __init__(self, *args, **named):
        """Dummy init to avoid conflicts in Python 2.6"""

    def coerce(cls, value):
        """Attempt to coerce the value using one of our baseType"""
        if isinstance(value, (str, unicode)):
            value = [value]
        if cls.check_single(value):
            value = [value]
        assert issubclass(cls, rlist.rlist)
        assert issubclass(cls, ListOf)
        newValue = cls()
        if isinstance(value, (str, unicode)):
            value = [value]
        newValue[:] = value
        return newValue

    def factories(cls):
        """Retrieve the list of factories for this class"""
        base = cls.baseType
        if base:
            if hasattr(base, 'factories'):
                return base.factories()
            else:
                return base
        return ()

    def coerce_single(cls, value):
        """coerce a single value to an acceptable type"""
        if cls.check_single(value):
            return value
        # needs actual coercion
        base = cls.baseType
        if base and hasattr(base, 'coerce'):
            return base.coerce(value)
        elif base:
            return base(value)
        return value

    def check(cls, value):
        """Check the whole set (debugging checks)"""
        if not isinstance(value, list):
            return 0
        base = cls.baseType
        if base:
            for item in value:
                if base and hasattr(base, 'check'):
                    if not base.check(item):
                        return 0
                elif base:
                    if not isinstance(item, base):
                        return 0
        return 1

    def check_single(cls, value):
        """Check whether a value is an instance of an acceptable type"""
        base = cls.baseType
        if base and hasattr(base, 'check'):
            return base.check(value)
        elif base:
            return isinstance(value, base)
        return 1

    def _get_name(self):
        if named.has_key('dataType'):
            dataType = named.get('dataType')
        elif hasattr(baseType, 'dataType'):
            dataType = baseType.dataType
        elif hasattr(baseType, '__name__'):
            dataType = baseType.__name__
        elif isinstance(baseType, str):
            # probably a string-specified data-type
            dataType = baseType.split('.')[-1]
        else:
            raise ValueError("""listof couldn't determine dataType specifier for %r"""%(baseType))

    def _get_baseType(self):
        """Get the baseType as an object/class"""
        base = getattr(self, '_baseType')
        if isinstance(base, type):
            return base
        if isinstance(base, unicode):
            base = str(base)
        if isinstance(base, (str, tuple)):
            new = latebind.bind(base)
            if isinstance(new, (tuple, list)):
                base = type(base)(new)
            else:
                base = new
        assert (
            isinstance(base, (type, types.ClassType)) or
            (
                hasattr(base, 'coerce') and
                hasattr(base, 'check')
            )
        ), """Specified base type %r for listof is not a class/type, and doesn't define both coerce and check methods"""%(
            base,
        )
        setattr(self, '_baseType', base)
        return base

    def _set_baseType(self, value):
        setattr(self, '_baseType', value)

    def _del_baseType(self, ):
        delattr(self, '_baseType')

    baseType = property(
            _get_baseType, _set_baseType, _del_baseType,
            doc="""The base-type specifier for the listof type"""
    )


listof_strings = listof(
        basic_types.String_DT,
        "listof_strings",
)
listof_ints = listof(
        basic_types.Int_DT,
        "listof_ints",
)
listof_bools = listof(
        basic_types.Boolean_DT,
        "listof_bools",
)
listof_longs = listof(
        basic_types.Long_DT,
        "listof_longs",
)
listof_floats = listof(
        basic_types.Float_DT,
        "listof_floats",
)
listof_classnames = listof(
        basic_types.ClassName_DT,
        "listof_classnames",
)
listof_classes = listof(
        basic_types.Class_DT,
        "listof_classes",
)
