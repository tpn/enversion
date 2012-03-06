
EVN_RPROPS_SCHEMA_VERSION = 1
EVN_RPROPS_SCHEMA = {
    1 : {
        'roots'     : dict,
        'notes'     : str,
        'errors'    : str,
        'warnings'  : str,
    },
}
assert EVN_RPROPS_SCHEMA_VERSION in EVN_RPROPS_SCHEMA

EVN_BRPROPS_SCHEMA_VERSION = 1
EVN_BRPROPS_SCHEMA = {
    1 : {
        'last_rev' : int,
        'version'  : int,
    },
}
assert EVN_BRPROPS_SCHEMA_VERSION in EVN_BRPROPS_SCHEMA

EVN_ERROR_CONFIRMATIONS = {
    e.RenameAffectsMultipleRoots : 'CONFIRM MULTI-ROOT RENAME',
}

EVN_ERROR_CONFIRMATION_BLURB = (
    "%s (if you're sure you want to perform this action, you can override"
    " this restriction by including the following text anywhere in the"
    " commit message: %s)"
)

class Constant(dict):
    def __init__(self):
        items = self.__class__.__dict__.items()
        for (key, value) in filter(lambda t: t[0][:2] != '__', items):
            try:
                self[value] = key
            except:
                pass
    def __getattr__(self, name):
        return self.__getitem__(name)
    def __setattr__(self, name, value):
        return self.__setitem__(name, value)
