# diff 2 strings using external diff
# and temp files. FIXME: move to a separate module
# later

import sys
import os

def diff_strings(oldstr, newstr):
    import tempfile

    try:
        (fd_new, name_new) = tempfile.mkstemp(prefix = 'oscpluginoverview.', suffix = '.diff', dir = '/tmp')
        (fd_old, name_old) = tempfile.mkstemp(prefix = 'oscpluginoverview.', suffix = '.diff', dir = '/tmp')

        os.write(fd_old, oldstr)
        os.write(fd_new, newstr)

        try:
            import commands
            (code, output) = commands.getstatusoutput("diff -u -w %s %s" % (name_old, name_new))
            if not (code/256):
                raise Exception("diff returned non zero")
            return output
        except:
            print "Can't execute diff: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
            exit(1)
    except:
        print "problem openting tempfile: %s %s" % (sys.exc_info()[0], sys.exc_info()[1])
        exit(1)
    else:
        file_new.close()
        file_old.close()
        os.unlink(name_new)
        os.unlink(name_old)

