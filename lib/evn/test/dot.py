stream = None
def dot(d=None):
    if not d:
        d = '.'
    stream.write(d)

def dash():
    dot('-')
