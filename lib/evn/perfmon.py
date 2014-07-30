#===============================================================================
# Imports
#===============================================================================
try:
    import psutil
except ImportError:
    pass

import itertools

from collections import (
    namedtuple,
)

from functools import (
    wraps,
)

#===============================================================================
# Named Tuples, Decorators & Helper Methods
#===============================================================================

ResourceUsageSnapshot = namedtuple(
    'ResourceUsageSnapshot', (
        'rss',
        'vms',
        'open_files',
        'num_threads',
        'cpu_percent',
        'cpu_sys_time',
        'cpu_user_time',
        'memory_percent',
    )
)

ResourceUsageDelta = namedtuple(
    'ResourceUsageDelta', (
        '%s_delta' % s for s in ResourceUsageSnapshot._fields
    ),
)

def track_resource_usage(f):
    @wraps(f)
    def wrapper(*args, **kwds):
        obj = args[0]
        if not obj._track_resource_usage:
            return f(*args, **kwds)
        else:
            with args[0]._track(f.func_name):
                return f(*args, **kwds)
    return wrapper

def create_resource_usage_snapshot(p):
    assert isinstance(p, psutil.Process)
    (rss, vms) = p.get_memory_info()
    (usr, sys) = p.get_cpu_times()
    return ResourceUsageSnapshot(
        rss,
        vms,
        len(p.get_open_files()),
        p.get_num_threads(),
        p.get_cpu_percent(),
        usr,
        sys,
        p.get_memory_percent()
    )

def create_resource_usage_delta(name, before, after):
    args = [
        (getattr(after, f) - getattr(before, f))
            for f in ResourceUsageSnapshot._fields
    ]
    return ResourceUsageDelta(*args)

#===============================================================================
# Classes
#===============================================================================
class ResourceUsageContainer(object):
    def __init__(self, name, depth, rss, vms):
        self.name = name
        self.depth = depth
        self.snapshots = list()
        self.deltas = list()

    def snapshot(self, msg, rss, vms):
        self.snapshots.append(ResourceUsageSnapshot(msg, rss, vms))

    def enter(self, name, rss, vms):
        self.snapshots.append(
            ResourceUsageSnapshotContext(name, self.depth+1, rss, vms)
        )

    def leave(self, rss, vms):
        self.snapshots.append(ResourceUsageSnapshot('leave', rss, vms))

    def __iter__(self):
        for snapshot in self.snapshots:
            if isinstance(snapshot, ResourceUsageSnapshot):
                yield snapshot
            else:
                assert isinstance(snapshot, ResourceUsageContainer)
                context = snapshot
                for snapshot in context:
                    yield snapshot

class ResourceUsageContext(object):
    def __init__(self, tracker, msg):
        self.msg     = msg
        self.after   = None
        self.depth   = None
        self.delta   = None
        self.before  = None
        self.tracker = tracker
        self.parent  = tracker.current_context

    def __enter__(self):
        self.before = create_resource_usage_snapshot(self.tracker.proc)
        self.depth = self.tracker._enter(self)
        return self

    def __exit__(self, *exc_info):
        self.after = create_resource_usage_snapshot(self.tracker.proc)
        args = (self.msg, self.before, self.after)
        self.delta = create_resource_usage_delta(*args)
        self.tracker._exit(self)

class ResourceUsageResultsFormatter(object):
    def format(self, name, value, context):
        attempts = itertools.count(0)
        return self._format(name, value, context, attempts)

    def _format(self, name, value, context, attempts):
        count = itertools.count(0)
        attempt = attempts.next()
        last_attempt = False
        try:
            if attempt == count.next():
                return getattr(self, name)(value, context)

            if attempt == count.next():
                return getattr(self, type(value).__name__)(value, context)

            if attempt == count.next():
                return str(value)

            last_attempt = True
        except:
            if not last_attempt:
                return self._format(name, value, context, attempts)
            else:
                m = "conversion failed for %s: %s" % (name, str(value))
                raise RuntimeError(m)

    def rss(self, value, context):
        return bytes_to_mb(value)

    def vms(self, value, context):
        return bytes_to_mb(value)

    def float(self, value, context):
        return '%0.3f' % value

    def name(self, value, context):
        prefix = '' if context.depth == 1 else ' ' * (context.depth * 2)
        return prefix + value


class ResourceUsageTracker(object):
    def __init__(self, msg):
        self.msg = msg
        self.proc = psutil.Process(os.getpid())
        self.current_depth = 0
        self.current_context = self
        self.previous_context = None
        self.contexts = list()

    @property
    def deltas(self):
        return (c.delta for c in self)

    def __iter__(self):
        return (c for c in self.contexts)

    def _enter(self, ctx):
        'Called by ResourceUsageContext.__enter__.  Returns current depth.'
        self.current_depth += 1
        self.previous_context = self.current_context
        self.current_context = ctx
        self.contexts.append(ctx)
        return self.current_depth

    def _exit(self, ctx):
        """Called by ResourceUsageContext.__exit__."""
        self.current_depth -= 1
        self.current_context = self.previous_context

    def track(self, msg):
        return ResourceUsageContext(self, msg)

    def get_results_header(self, exclude=None):
        return tuple(
            ('name', ) + tuple(
                f for f in ResourceUsageSnapshot._fields
                    if not exclude or not exclude(f)
            )
        )

    def get_results(self, formatter=None, exclude=None):
        if not formatter:
            formatter = ResourceUsageResultsFormatter()

        return ( [
            (formatter.format(name, value, context))
                for (name, value) in chain(
                    (('name', context.msg),), zip(
                        ResourceUsageSnapshot._fields,
                        context.delta,
                    )
                ) if not exclude or not exclude(name)
            ] for context in self.contexts
        )

        return (
            [ ' ' * context.msg, ] + [
                (formatter.format(name, value))
                    for (name, value) in zip(
                        ResourceUsageSnapshot._fields,
                        context.delta,
                    ) if not exclude or not exclude(name)
            ] for context in self.contexts
        )

    def results_to_table(self, output=None, formatter=None, exclude=None):
        if not output:
            output = sys.stdout

        if not formatter:
            formatter = ResourceUsageResultsFormatter()

        if not exclude:
            pass

        k = Dict()
        k.output  = output
        k.banner  = "%s: Resource Usage Deltas" % self.msg
        k.formats = lambda: chain((str.ljust,), repeat(str.rjust))

        results = chain(
            (self.get_results_header(exclude=exclude),),
            self.get_results(formatter=formatter, exclude=exclude)
        )
        render_text_table(results, **k)

class DummyResourceUsageTracker(object):
    def track(self, *args):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

# vim:set ts=8 sw=4 sts=4 tw=78 et:
