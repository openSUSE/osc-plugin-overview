import tempfile

def diff_strings(oldstr, newstr):
    """diff two strings using external diff
    difflib does not support -w (ignoring whitespace)
    """
    with tempfile.NamedTemporaryFile('w') as tmp1, tempfile.NamedTemporaryFile('w') as tmp2:
        tmp1.write(oldstr)
        tmp2.write(newstr)
        tmp1.flush()
        tmp2.flush()

        import subprocess
        p = subprocess.Popen(["diff", "-u", '-w', tmp1.name, tmp2.name], stdout=subprocess.PIPE)
        output = p.communicate()[0]
        code = p.returncode
        if code > 2:
            raise Exception("diff returned error: %d" % code)
        return output

