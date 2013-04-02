import sys
import os
import os.path

# Make sure that charmsupport is importable, or bail out.
try:
    import charmsupport
    _ = charmsupport
except ImportError:
    local_copy = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "lib", "charmsupport")
    if not os.path.exists(local_copy) or not os.path.isdir(local_copy):
        sys.exit("Could not find required 'charmsupport' library.")
    sys.path.insert(0, local_copy)

# Make sure that charmhelpers is importable, or bail out.
try:
    import charmhelpers
    _ = charmhelpers
except ImportError:
    local_copy = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "lib", "charm-tools", "helpers", "python")
    if not os.path.exists(local_copy) or not os.path.isdir(local_copy):
        sys.exit("Could not find required 'charmhelpers' library.")
    sys.path.insert(0, local_copy)

# Make sure that shelltoolbox is importable, or bail out.
try:
    import shelltoolbox
    _ = shelltoolbox
except ImportError:
    local_copy = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "lib", "shelltoolbox")
    if not os.path.exists(local_copy) or not os.path.isdir(local_copy):
        sys.exit("Could not find required 'shelltoolbox' library.")
    sys.path.insert(0, local_copy)
