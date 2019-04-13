'''
print -- CSLabs Print Server
conf -- Configuration

This module contains some variables that can be modified to configure the web
application. In general, these variables are used to provide defaults for
actions that are done via the web interface. They should not be used in any
other scenario, particularly in places where the web interface is irrelevant.

The following are defined:
* ALLOWED_EXTENSIONS are the file extensions the print API will consider
    printing directly.
* CONVERTABLE_EXTENSIONS are the file extension the print API will try to
    convert to PDF befire printing.
'''

ALLOWED_EXTENSIONS = sorted(["txt", "pdf", "ps", "png", "jpg", "jpeg", "gif",
    "tex", "prn", "c", "cpp", "h", "hpp", "java", "pl", "py", "php", "sh", "b",
    "xml", "conf", "asm", "bat", "bib", "cs", "erl", "ini", "js", "lisp", "sql",
    "m", "pas", "patch", "pro", "scm", "hs", "sol"])
CONVERTABLE_EXTENSIONS = sorted(["docx", "doc","odt","pptx","ppt","odp","xlsx",
    "xls","ods","csv","odf","odg","rtf"])
ALL_EXTENSIONS = sorted(ALLOWED_EXTENSIONS+CONVERTABLE_EXTENSIONS)
