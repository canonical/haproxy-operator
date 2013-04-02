import sys
import os
import os.path

# Make sure that charmsupport is importable, or bail out.
local_copy = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "lib", "charmsupport")
if os.path.exists(local_copy) and os.path.isdir(local_copy):
    sys.path.insert(0, local_copy)

try:
    import charmsupport
    _ = charmsupport
except ImportError:
    sys.exit("Could not find required 'charmsupport' library.")

# Make sure that shelltoolbox is importable, or bail out.
local_copy = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "lib", "shelltoolbox")
if os.path.exists(local_copy) and os.path.isdir(local_copy):
    sys.path.insert(0, local_copy)
try:
    import shelltoolbox
    _ = shelltoolbox
except ImportError:
    sys.exit("Could not find required 'shelltoolbox' library.")

# Make sure that charmhelpers is importable, or bail out.
local_copy = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "lib", "charm-tools", "helpers", "python")
if os.path.exists(local_copy) and os.path.isdir(local_copy):
    sys.path.insert(0, local_copy)
try:
    import charmhelpers
    _ = charmhelpers
except ImportError:
    sys.exit("Could not find required 'charmhelpers' library.")
