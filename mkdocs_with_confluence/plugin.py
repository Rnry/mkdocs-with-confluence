# PYLINT_COMMENT: plugin.py:1:0: C0114: Missing module docstring (missing-module-docstring)
# PYLINT_COMMENT: How to fix: Add a docstring at the beginning of the file (e.g., """MkDocs plugin to export pages to Confluence.""").
# PYLINT_COMMENT: Why: Provides a high-level overview of the module's purpose.
import time
import os
import hashlib
import sys
import re
import tempfile
import shutil
# PYLINT_COMMENT: plugin.py:9:0: C0411: standard import "mimetypes" should be placed before third party import "requests" (wrong-import-order)
# PYLINT_COMMENT: How to fix: Group standard library imports first, then third-party, then local application imports. Move mimetypes before requests.
# PYLINT_COMMENT: Why: Standard practice for readability and consistency (PEP 8).
import requests
import mimetypes
# PYLINT_COMMENT: plugin.py:11:0: C0411: standard import "contextlib" should be placed before third party imports "requests", "mistune" (wrong-import-order)
# PYLINT_COMMENT: How to fix: Move contextlib before requests and mistune.
# PYLINT_COMMENT: Why: PEP 8 import grouping.
import mistune
import contextlib
# PYLINT_COMMENT: plugin.py:12:0: C0411: standard import "time.sleep" should be placed before third party imports "requests", "mistune" (wrong-import-order)
# PYLINT_COMMENT: How to fix: `from time import sleep` is a standard library import. It should be grouped with other standard imports like `time`, `os`, etc., or if kept separate, still before third-party.
# PYLINT_COMMENT: Why: PEP 8 import grouping.
from time import sleep
from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin
from md2cf.confluence_renderer import ConfluenceRenderer
# PYLINT_COMMENT: plugin.py:16:0: C0411: standard import "os.environ" should be placed before third party imports "requests", "mistune", "mkdocs.config.config_options", "mkdocs.plugins.BasePlugin", "md2cf.confluence_renderer.ConfluenceRenderer" (wrong-import-order)
# PYLINT_COMMENT: How to fix: `from os import environ` is a standard library import. Group it with other standard imports.
# PYLINT_COMMENT: Why: PEP 8 import grouping.
from os import environ
# PYLINT_COMMENT: plugin.py:17:0: C0411: standard import "pathlib.Path" should be placed before third party imports "requests", "mistune", "mkdocs.config.config_options", "mkdocs.plugins.BasePlugin", "md2cf.confluence_renderer.ConfluenceRenderer" (wrong-import-order)
# PYLINT_COMMENT: How to fix: `from pathlib import Path` is a standard library import. Group it with other standard imports.
# PYLINT_COMMENT: Why: PEP 8 import grouping.
from pathlib import Path

TEMPLATE_BODY = "<p> TEMPLATE </p>"


@contextlib.contextmanager
# PYLINT_COMMENT: plugin.py:23:0: C0116: Missing function or method docstring (missing-function-docstring)
# PYLINT_COMMENT: How to fix: Add a docstring, e.g., """Temporarily suppresses stdout by redirecting it to a dummy file."""
# PYLINT_COMMENT: Why: Explains the function's purpose, arguments, and behavior.
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout


# PYLINT_COMMENT: plugin.py:30:0: C0115: Missing class docstring (missing-class-docstring)
# PYLINT_COMMENT: How to fix: Add a docstring, e.g., """A dummy file-like object that discards all writes."""
# PYLINT_COMMENT: Why: Explains the class's purpose.
# PYLINT_COMMENT: plugin.py:30:0: R0205: Class 'DummyFile' inherits from object, can be safely removed from bases in python3 (useless-object-inheritance)
# PYLINT_COMMENT: How to fix: Change `class DummyFile(object):` to `class DummyFile:`.
# PYLINT_COMMENT: Why: In Python 3, inheriting from `object` is implicit and therefore redundant.
# PYLINT_COMMENT: plugin.py:30:0: R0903: Too few public methods (1/2) (too-few-public-methods)
# PYLINT_COMMENT: How to fix: This class is simple and likely fine. If Pylint is too strict, this can be disabled with `# pylint: disable=too-few-public-methods`. Otherwise, consider if the class truly needs to exist or if its functionality can be merged.
# PYLINT_COMMENT: Why: Pylint flags classes with very few methods as they might not justify their existence as a class. However, for simple helper objects like this, it's often acceptable.
class DummyFile(object):
    # PYLINT_COMMENT: plugin.py:31:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add a docstring, e.g., """Silently discards any data written."""
    # PYLINT_COMMENT: Why: Explains the method's behavior.
    def write(self, x):
        pass


# PYLINT_COMMENT: plugin.py:35:0: C0115: Missing class docstring (missing-class-docstring)
# PYLINT_COMMENT: How to fix: Add a docstring, e.g., """An MkDocs plugin to synchronize documentation pages with a Confluence space."""
# PYLINT_COMMENT: Why: Explains the class's purpose and overall functionality.
# PYLINT_COMMENT: plugin.py:35:0: R0902: Too many instance attributes (14/7) (too-many-instance-attributes)
# PYLINT_COMMENT: How to fix: Review attributes. Some (like `page_title`, `section_title` if only used temporarily in `on_nav`) might be refactored to be local variables or passed as parameters. Alternatively, group related attributes into a separate data class/object if logical. If all are necessary, this warning can be locally disabled.
# PYLINT_COMMENT: Why: Many instance attributes can make a class harder to understand and maintain.
class MkdocsWithConfluence(BasePlugin):
    _id = 0
    config_scheme = (
        ("host_url", config_options.Type(str, default=None)),
        ("space", config_options.Type(str, default=None)),
        ("parent_page_name", config_options.Type(str, default=None)),
        ("username", config_options.Type(str, default=environ.get("JIRA_USERNAME", None))),
        ("api_token", config_options.Type(str, default=environ.get("CONFLUENCE_API_TOKEN", None))), # If specified, password is ignored
        ("password", config_options.Type(str, default=environ.get("JIRA_PASSWORD", None))),
        ("enabled_if_env", config_options.Type(str, default=None)),
        ("verbose", config_options.Type(bool, default=False)),
        ("debug", config_options.Type(bool, default=False)),
        ("dryrun", config_options.Type(bool, default=False)),
    )

    def __init__(self):
        self.enabled = True
        self.confluence_renderer = ConfluenceRenderer(use_xhtml=True)
        self.confluence_mistune = mistune.Markdown(renderer=self.confluence_renderer)
        self.simple_log = False
        self.flen = 1
        self.session = requests.Session()
        self.page_attachments = {}
        # PYLINT_COMMENT: Consider initializing attributes like self.dryrun here (e.g., self.dryrun = False) to address W0201 later.
        # PYLINT_COMMENT: Attributes like self.page_title, self.page_local_path etc. if they are intended to be instance attributes, should also be initialized here, e.g. self.page_title = None.

    # PYLINT_COMMENT: plugin.py:59:4: W0221: Number of parameters was 2 in 'BasePlugin.on_nav' and is now 4 in overriding 'MkdocsWithConfluence.on_nav' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Ensure the method signature matches the parent class `BasePlugin.on_nav(self, nav, **kwargs)`. If `config` and `files` are needed, they should be part of `**kwargs` or the parent method signature should be checked for compatibility. MkDocs plugin event methods usually have specific signatures like `on_nav(self, nav, config, files)`. If `BasePlugin` is a custom base, update it. If it's MkDocs' `BasePlugin`, this signature is standard. This Pylint warning might be a false positive if the `BasePlugin` definition Pylint sees is incorrect or outdated.
    # PYLINT_COMMENT: Why: Overridden methods should have compatible signatures with their parent methods to maintain polymorphism and prevent unexpected errors.
    def on_nav(self, nav, config, files):
        MkdocsWithConfluence.tab_nav = []
        # PYLINT_COMMENT: plugin.py:61:27: C2801: Unnecessarily calls dunder method __repr__. Use repr built-in function. (unnecessary-dunder-call)
        # PYLINT_COMMENT: How to fix: Change `nav.__repr__()` to `repr(nav)`.
        # PYLINT_COMMENT: Why: `repr()` is the idiomatic way to get the string representation an object is designed to provide via its `__repr__` method. Direct dunder calls are generally discouraged.
        navigation_items = nav.__repr__()

        for n in navigation_items.split("\n"):
            leading_spaces = len(n) - len(n.lstrip(" "))
            spaces = leading_spaces * " "
            if "Page" in n:
                try:
                    # PYLINT_COMMENT: plugin.py:68:20: W0201: Attribute 'page_title' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.page_title = None` (or a suitable default) in the `__init__` method.
                    # PYLINT_COMMENT: Why: All instance attributes should ideally be declared in `__init__` for clarity and to ensure they always exist.
                    self.page_title = self.__get_page_title(n)
                    if self.page_title is None:
                        raise AttributeError
                except AttributeError:
                    # PYLINT_COMMENT: plugin.py:72:20: W0201: Attribute 'page_local_path' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.page_local_path = None` in `__init__`.
                    # PYLINT_COMMENT: Why: Clarity and ensuring attribute existence.
                    self.page_local_path = self.__get_page_url(n)
                    print(
                        f"WARN     - Page from path {self.page_local_path} has no"
                        f"         entity in the mkdocs.yml nav section. It will be uploaded"
                        f"         to the Confluence, but you may not see it on the web server!"
                    )
                    # PYLINT_COMMENT: plugin.py:78:20: W0201: Attribute 'page_local_name' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.page_local_name = None` in `__init__`.
                    # PYLINT_COMMENT: Why: Clarity and ensuring attribute existence.
                    self.page_local_name = self.__get_page_name(n)
                    # PYLINT_COMMENT: plugin.py:79:20: W0201: Attribute 'page_title' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: (Already noted above, ensure it's initialized in __init__)
                    self.page_title = self.page_local_name

                p = spaces + self.page_title
                MkdocsWithConfluence.tab_nav.append(p)
            if "Section" in n:
                try:
                    # PYLINT_COMMENT: plugin.py:85:20: W0201: Attribute 'section_title' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.section_title = None` in `__init__`.
                    # PYLINT_COMMENT: Why: Clarity and ensuring attribute existence.
                    self.section_title = self.__get_section_title(n)
                    if self.section_title is None:
                        raise AttributeError
                except AttributeError:
                    # PYLINT_COMMENT: plugin.py:89:20: W0201: Attribute 'section_local_path' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.section_local_path = None` in `__init__`.
                    # PYLINT_COMMENT: Why: Clarity and ensuring attribute existence.
                    self.section_local_path = self.__get_page_url(n)
                    print(
                        f"WARN     - Section from path {self.section_local_path} has no"
                        f"         entity in the mkdocs.yml nav section. It will be uploaded"
                        f"         to the Confluence, but you may not see it on the web server!"
                    )
                    # PYLINT_COMMENT: plugin.py:95:20: W0201: Attribute 'section_local_name' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: How to fix: Initialize `self.section_local_name = None` in `__init__`.
                    # PYLINT_COMMENT: Why: Clarity and ensuring attribute existence.
                    self.section_local_name = self.__get_section_title(n) # This seems to be calling __get_section_title again, might be a bug, maybe intended self.__get_section_name(n)?
                    # PYLINT_COMMENT: plugin.py:96:20: W0201: Attribute 'section_title' defined outside __init__ (attribute-defined-outside-init)
                    # PYLINT_COMMENT: (Already noted above, ensure it's initialized in __init__)
                    self.section_title = self.section_local_name
                s = spaces + self.section_title
                MkdocsWithConfluence.tab_nav.append(s)

    # PYLINT_COMMENT: plugin.py:100:4: W0221: Number of parameters was 1 in 'BasePlugin.on_files' and is now 3 in overriding 'MkdocsWithConfluence.on_files' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Similar to `on_nav`, check the expected signature for `on_files` in `BasePlugin`. MkDocs standard is `on_files(self, files, config)`. If `BasePlugin` is custom, align them. If Pylint's view of MkDocs' `BasePlugin` is outdated, this might be a false positive.
    # PYLINT_COMMENT: Why: Method signature consistency.
    def on_files(self, files, config):
        pages = files.documentation_pages()
        try:
            self.flen = len(pages)
            print(f"Number of Files in directory tree: {self.flen}")
        # PYLINT_COMMENT: plugin.py:105:15: E0712: Catching an exception which doesn't inherit from Exception: 0 (catching-non-exception)
        # PYLINT_COMMENT: How to fix: Change `except 0:` to `except TypeError:`. The `len()` function doesn't raise `0`. This `try...except` block seems to misunderstand how `len()` works. An empty list returns `0`, not an error. The check should be `if not pages:` or `if len(pages) == 0:`.
        # PYLINT_COMMENT: Why: `except 0:` is syntactically incorrect for catching exceptions. Exceptions are classes inheriting from `BaseException`.
        except 0:
            # PYLINT_COMMENT: plugin.py:106:0: W1404: Implicit string concatenation found in call (implicit-str-concat)
            # PYLINT_COMMENT: How to fix: Combine the two strings with a `+` or make them part of a single f-string/string literal: `print("ERR: You have no documentation pages in the directory tree, please add at least one!")`
            # PYLINT_COMMENT: Why: Implicit string concatenation (two string literals side-by-side) can be less readable than explicit concatenation.
            print("ERR: You have no documentation pages" "in the directory tree, please add at least one!")

    # PYLINT_COMMENT: plugin.py:108:4: W0221: Number of parameters was 2 in 'BasePlugin.on_post_template' and is now 4 in overriding 'MkdocsWithConfluence.on_post_template' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Check `BasePlugin` for `on_post_template`'s signature. MkDocs standard is `on_post_template(self, output_content, template_name, config)`. Similar reasoning as `on_nav`.
    # PYLINT_COMMENT: Why: Method signature consistency.
    def on_post_template(self, output_content, template_name, config):
        if self.config["verbose"] is False and self.config["debug"] is False:
            self.simple_log = True
            print("INFO     -  Mkdocs With Confluence: Start exporting markdown pages... (simple logging)")
        else:
            self.simple_log = False

    def on_config(self, config):
        if "enabled_if_env" in self.config:
            env_name = self.config["enabled_if_env"]
            if env_name:
                self.enabled = os.environ.get(env_name) == "1"
                if not self.enabled:
                    print(
                        "WARNING - Mkdocs With Confluence: Exporting MKDOCS pages to Confluence turned OFF: "
                        f"(set environment variable {env_name} to 1 to enable)"
                    )
                    return
                # PYLINT_COMMENT: plugin.py:120:16: R1705: Unnecessary "else" after "return", remove the "else" and de-indent the code inside it (no-else-return)
                # PYLINT_COMMENT: How to fix: Remove the `else:` and unindent the following block.
                # PYLINT_COMMENT: Why: When an `if` block contains a `return`, the `else` is redundant because the code in the `else` block will only be reached if the `if` condition was false.
                else:
                    print(
                        "INFO     -  Mkdocs With Confluence: Exporting MKDOCS pages to Confluence "
                        f"turned ON by var {env_name}==1!"
                    )
                    self.enabled = True # This is redundant if already set based on env var.
            else:
                print(
                    "WARNING -  Mkdocs With Confluence: Exporting MKDOCS pages to Confluence turned OFF: "
                    f"(set environment variable {env_name} to 1 to enable)"
                )
                return # Missing return if env_name is None but "enabled_if_env" key exists. This branch implies it's disabled.
        else:
            print("INFO     -  Mkdocs With Confluence: Exporting MKDOCS pages to Confluence turned ON by default!")
            self.enabled = True

        if self.config["dryrun"]:
            print("WARNING -  Mkdocs With Confluence - DRYRUN MODE turned ON")
            # PYLINT_COMMENT: plugin.py:144:12: W0201: Attribute 'dryrun' defined outside __init__ (attribute-defined-outside-init)
            # PYLINT_COMMENT: How to fix: Initialize `self.dryrun = False` (or a suitable default from config) in the `__init__` method.
            # PYLINT_COMMENT: Why: All instance attributes should ideally be declared in `__init__`.
            self.dryrun = True
        else:
            # PYLINT_COMMENT: plugin.py:146:12: W0201: Attribute 'dryrun' defined outside __init__ (attribute-defined-outside-init)
            # PYLINT_COMMENT: (Already noted above)
            self.dryrun = False

    # PYLINT_COMMENT: plugin.py:148:4: W0221: Number of parameters was 3 in 'BasePlugin.on_page_markdown' and is now 5 in overriding 'MkdocsWithConfluence.on_page_markdown' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Check `BasePlugin` for `on_page_markdown`'s signature. MkDocs standard is `on_page_markdown(self, markdown, page, config, files)`. Similar reasoning as `on_nav`.
    # PYLINT_COMMENT: Why: Method signature consistency.
    # PYLINT_COMMENT: plugin.py:148:4: R0914: Too many local variables (26/15) (too-many-locals)
    # PYLINT_COMMENT: How to fix: Refactor the method. Extract parts of its logic into smaller helper methods. This can reduce the number of variables needed in the main method's scope.
    # PYLINT_COMMENT: Why: Methods with too many local variables can be hard to follow and debug.
    # PYLINT_COMMENT: plugin.py:148:4: R0912: Too many branches (58/12) (too-many-branches)
    # PYLINT_COMMENT: How to fix: Refactor into smaller methods. Complex conditional logic can often be simplified or encapsulated.
    # PYLINT_COMMENT: Why: High branching complexity makes code harder to test, understand, and maintain.
    # PYLINT_COMMENT: plugin.py:148:4: R0915: Too many statements (134/50) (too-many-statements)
    # PYLINT_COMMENT: How to fix: Break down this very long method into several smaller, more focused helper methods.
    # PYLINT_COMMENT: Why: Long methods are difficult to read, understand, and maintain.
    def on_page_markdown(self, markdown, page, config, files):
        MkdocsWithConfluence._id += 1
        if self.config["api_token"]:
            self.session.auth = (self.config["username"], self.config["api_token"])
        else:
            self.session.auth = (self.config["username"], self.config["password"])

        if self.enabled:
            if self.simple_log is True:
                print("INFO     - Mkdocs With Confluence: Page export progress: [", end="", flush=True)
                for i in range(MkdocsWithConfluence._id):
                    print("#", end="", flush=True)
                # PYLINT_COMMENT: plugin.py:160:20: W0612: Unused variable 'j' (unused-variable)
                # PYLINT_COMMENT: How to fix: If 'j' is truly not needed, replace `for j in ...` with `for _ in ...`.
                # PYLINT_COMMENT: Why: Unused variables can be confusing and might indicate a bug or incomplete logic.
                for j in range(self.flen - MkdocsWithConfluence._id):
                    print("-", end="", flush=True)
                print(f"] ({MkdocsWithConfluence._id} / {self.flen})", end="\r", flush=True)

            if self.config["debug"]:
                print(f"\nDEBUG     - Handling Page '{page.title}' (And Parent Nav Pages if necessary):\n")
            if not all(self.config_scheme): # This check seems logically flawed. config_scheme is a definition, not values.
                                          # It likely intends to check if required self.config values are present.
                print("DEBUG     - ERR: YOU HAVE EMPTY VALUES IN YOUR CONFIG. ABORTING")
                return markdown

            try:
                if self.config["debug"]:
                    print("DEBUG     - Get section first parent title...: ")
                try:
                    # PYLINT_COMMENT: plugin.py:175:54: C2801: Unnecessarily calls dunder method __repr__. Use repr built-in function. (unnecessary-dunder-call)
                    # PYLINT_COMMENT: How to fix: Change `page.ancestors[0].__repr__()` to `repr(page.ancestors[0])`.
                    # PYLINT_COMMENT: Why: Use the `repr()` built-in.
                    parent = self.__get_section_title(page.ancestors[0].__repr__())
                except IndexError as e:
                    if self.config["debug"]:
                        print(
                            f"DEBUG     - WRN({e}): No first parent! Assuming "
                            f"DEBUG     - {self.config['parent_page_name']}..."
                        )
                    parent = None
                if self.config["debug"]:
                    print(f"DEBUG     - {parent}")
                if not parent:
                    parent = self.config["parent_page_name"]

                if self.config["parent_page_name"] is not None:
                    main_parent = self.config["parent_page_name"]
                else:
                    main_parent = self.config["space"] # main_parent can be space name if parent_page_name is not set.

                if self.config["debug"]:
                    print("DEBUG     - Get section second parent title...: ")
                try:
                    # PYLINT_COMMENT: plugin.py:196:55: C2801: Unnecessarily calls dunder method __repr__. Use repr built-in function. (unnecessary-dunder-call)
                    # PYLINT_COMMENT: How to fix: Change `page.ancestors[1].__repr__()` to `repr(page.ancestors[1])`.
                    # PYLINT_COMMENT: Why: Use the `repr()` built-in.
                    parent1 = self.__get_section_title(page.ancestors[1].__repr__())
                except IndexError as e:
                    if self.config["debug"]:
                        print(
                            f"DEBUG     - ERR({e}) No second parent! Assuming "
                            f"second parent is main parent: {main_parent}..."
                        )
                    parent1 = None
                if self.config["debug"]:
                    print(f"{parent}") # This prints 'parent', did you mean 'parent1'?

                if not parent1:
                    parent1 = main_parent
                    if self.config["debug"]:
                        print(
                            f"DEBUG     - ONLY ONE PARENT FOUND. ASSUMING AS A "
                            f"FIRST NODE after main parent config {main_parent}"
                        )

                if self.config["debug"]:
                    print(f"DEBUG     - PARENT0: {parent}, PARENT1: {parent1}, MAIN PARENT: {main_parent}")

                # PYLINT_COMMENT: plugin.py:218:21: R1732: Consider using 'with' for resource-allocating operations (consider-using-with)
                # PYLINT_COMMENT: How to fix: Use `with tempfile.NamedTemporaryFile(delete=False, mode="w", encoding="utf-8") as tf:`
                # PYLINT_COMMENT: Why: `with` statement ensures resources are properly managed (e.g., file is closed automatically). `delete=False` is tricky, ensure cleanup.
                tf = tempfile.NamedTemporaryFile(delete=False)
                # PYLINT_COMMENT: plugin.py:219:20: R1732: Consider using 'with' for resource-allocating operations (consider-using-with)
                # PYLINT_COMMENT: How to fix: If tf is managed with `with`, this `open` might be part of it or use `with open(tf.name, "w", encoding="utf-8") as f:`.
                # PYLINT_COMMENT: Why: Ensures file is closed.
                # PYLINT_COMMENT: plugin.py:219:20: W1514: Using open without explicitly specifying an encoding (unspecified-encoding)
                # PYLINT_COMMENT: How to fix: Add `encoding="utf-8"` (or another appropriate encoding) to the `open()` call: `f = open(tf.name, "w", encoding="utf-8")`.
                # PYLINT_COMMENT: Why: Makes the code platform-independent and less prone to encoding errors.
                f = open(tf.name, "w")

                attachments = []
                try:
                    for match in re.finditer(r'img src="file://(.*)" s', markdown): # Regex looks suspicious: ' s' at the end.
                        if self.config["debug"]:
                            print(f"DEBUG     - FOUND IMAGE: {match.group(1)}")
                        attachments.append(match.group(1))
                    for match in re.finditer(r"!\[[\w\. -]*\]\((?!http|file)([^\s,]*).*\)", markdown):
                        file_path = match.group(1).lstrip("./\\")
                        attachments.append(file_path)

                        if self.config["debug"]:
                            print(f"DEBUG     - FOUND IMAGE: {file_path}")
                        # This path manipulation might be fragile:
                        attachments.append("docs/" + file_path.replace("../", ""))

                except AttributeError as e: # This except may not be correctly placed for re.finditer
                    if self.config["debug"]:
                        print(f"DEBUG     - WARN(({e}): No images found in markdown. Proceed..")
                new_markdown = re.sub(
                    r'<img src="file:///tmp/', '<p><ac:image ac:height="350"><ri:attachment ri:filename="', markdown # Hardcoded /tmp/
                )
                new_markdown = re.sub(r'" style="page-break-inside: avoid;">', '"/></ac:image></p>', new_markdown)
                confluence_body = self.confluence_mistune(new_markdown)
                f.write(confluence_body)
                if self.config["debug"]:
                    print(confluence_body)
                page_name = page.title
                new_name = "confluence_page_" + page_name.replace(" ", "_") + ".html"
                shutil.copy(f.name, new_name)
                f.close() # Should be in a finally block if not using 'with'

                if self.config["debug"]:
                    print(
                        f"\nDEBUG     - UPDATING PAGE TO CONFLUENCE, DETAILS:\n"
                        f"DEBUG     - HOST: {self.config['host_url']}\n"
                        f"DEBUG     - SPACE: {self.config['space']}\n"
                        f"DEBUG     - TITLE: {page.title}\n"
                        f"DEBUG     - PARENT: {parent}\n"
                        f"DEBUG     - BODY: {confluence_body}\n" # This can be very long for debug output
                    )

                page_id = self.find_page_id(page.title)
                if page_id is not None:
                    if self.config["debug"]:
                        print(
                            f"DEBUG     - JUST ONE STEP FROM UPDATE OF PAGE '{page.title}' \n"
                            f"DEBUG     - CHECKING IF PARENT PAGE ON CONFLUENCE IS THE SAME AS HERE"
                        )

                    parent_name = self.find_parent_name_of_page(page.title)

                    if parent_name == parent:
                        if self.config["debug"]:
                            print("DEBUG     - Parents match. Continue...")
                    else:
                        if self.config["debug"]:
                            print(f"DEBUG     - ERR, Parents does not match: '{parent}' =/= '{parent_name}' Aborting...")
                        return markdown # Early return if parents don't match
                    self.update_page(page.title, confluence_body)
                    for i in MkdocsWithConfluence.tab_nav:
                        if page.title in i:
                            print(f"INFO     - Mkdocs With Confluence: {i} *UPDATE*")
                else: # page_id is None, so create page and potentially parents
                    if self.config["debug"]:
                        print(
                            f"DEBUG     - PAGE: {page.title}, PARENT0: {parent}, "
                            f"PARENT1: {parent1}, MAIN PARENT: {main_parent}"
                        )
                    parent_id = self.find_page_id(parent) # Re-fetch parent_id; it was already fetched for 'parent' name
                    self.wait_until(parent_id, 1, 20) # This wait_until logic might be flawed.
                                                     # It waits if parent_id is None, doesn't re-fetch.
                    second_parent_id = self.find_page_id(parent1)
                    self.wait_until(second_parent_id, 1, 20)
                    main_parent_id = self.find_page_id(main_parent) # ID for space name? Confluence API usually doesn't provide page ID for space itself.

                    if not parent_id: # parent (ancestor[0]) does not exist
                        if not second_parent_id: # parent1 (ancestor[1]) does not exist
                            # main_parent_id = self.find_page_id(main_parent) # Fetched again
                            if not main_parent_id:
                                # This typically means the "parent_page_name" from config (or space itself if parent_page_name is None) wasn't found.
                                # If main_parent is the space key, find_page_id might not work as expected unless there's a page titled with the space key.
                                print("ERR: MAIN PARENT UNKNOWN. ABORTING!")
                                return markdown

                            if self.config["debug"]:
                                print(
                                    f"DEBUG     - Trying to ADD page '{parent1}' to " # parent1 is the first to be created under main_parent
                                    f"main parent({main_parent}) ID: {main_parent_id}"
                                )
                            body = TEMPLATE_BODY.replace("TEMPLATE", parent1)
                            self.add_page(parent1, main_parent_id, body)
                            for i_tab in MkdocsWithConfluence.tab_nav: # Renamed 'i' to 'i_tab' for clarity
                                if parent1 in i_tab:
                                    print(f"INFO     - Mkdocs With Confluence: {i_tab} *NEW PAGE*")
                            time.sleep(1) # Allow Confluence to process
                            second_parent_id = self.find_page_id(parent1) # Get ID of newly created parent1

                        # Now, second_parent_id should exist (either found or created)
                        # Create 'parent' under 'parent1'
                        if self.config["debug"]:
                            print(
                                f"DEBUG     - Trying to ADD page '{parent}' "
                                f"to parent1({parent1}) ID: {second_parent_id}"
                            )
                        body = TEMPLATE_BODY.replace("TEMPLATE", parent)
                        # If second_parent_id is still None here (e.g. creation failed or main_parent was space), this will fail.
                        self.add_page(parent, second_parent_id, body)
                        for i_tab in MkdocsWithConfluence.tab_nav:
                            if parent in i_tab:
                                print(f"INFO     - Mkdocs With Confluence: {i_tab} *NEW PAGE*")
                        time.sleep(1)
                        parent_id = self.find_page_id(parent) # Get ID of newly created parent

                    # Retry loop for adding the actual page if its direct parent_id was initially None
                    # This retry logic is a bit convoluted and might try to add with parent_id = None
                    if parent_id is None: # This condition suggests the parent page (parent) was NOT successfully created or found by find_page_id.
                                         # The previous block should have created `parent` and assigned its ID to `parent_id`.
                                         # This retry loop might be redundant or indicate an issue in the logic above.
                        for i_retry in range(11): # Renamed 'i'
                            # The `while parent_id is None:` loop inside the `for` loop is problematic.
                            # If `parent_id` is `None`, it will enter the `while`.
                            # If `add_page` throws HTTPError, it sleeps, calls `find_page_id`, and then `break`s the `while` loop.
                            # The outer `for` loop continues. This structure needs careful review.
                            while parent_id is None: # This should ideally not be needed if parent creation logic above is robust.
                                try:
                                    # If parent_id is None, this add_page call will likely fail if parent_id is required.
                                    self.add_page(page.title, parent_id, confluence_body)
                                    # If add_page succeeds (which is unlikely if parent_id is None and required), then parent_id would still be None here
                                    # leading to an infinite loop unless add_page itself sets self.parent_id or something similar which is not the case.
                                    # This loop seems to be trying to add the child page repeatedly with a potentially None parent_id.
                                    break # Exit while if add_page succeeds.
                                except requests.exceptions.HTTPError:
                                    print(
                                        f"ERR     - HTTP error on adding page. It probably occured due to "
                                        f"parent ID('{parent_id}') page is not YET synced on server. Retry nb {i_retry}/10..."
                                    )
                                    sleep(5)
                                    parent_id = self.find_page_id(parent) # Attempt to re-find the PARENT's ID.
                                    # If parent_id is found, the while loop condition (parent_id is None) becomes false for the next iteration.
                                # break # This break exits the while loop after one attempt (either success or HTTPError)
                            if parent_id is not None: # If parent ID was found after retry, break the for loop
                                break
                        # If after retries, parent_id is still None, the next add_page will likely fail.

                    # This add_page call happens regardless of the retry loop's success in finding parent_id.
                    # If parent_id is still None, this will attempt to add with a None parent_id.
                    self.add_page(page.title, parent_id, confluence_body)

                    # This print might be misleading if parent_id is None
                    print(f"Trying to ADD page '{page.title}' to parent0({parent}) ID: {parent_id}")
                    for i_tab in MkdocsWithConfluence.tab_nav:
                        if page.title in i_tab:
                            print(f"INFO     - Mkdocs With Confluence: {i_tab} *NEW PAGE*")

                if attachments:
                    self.page_attachments[page.title] = attachments

            except IndexError as e: # This top-level IndexError might catch errors from page.ancestors if not handled by inner try-excepts
                if self.config["debug"]:
                    print(f"DEBUG     - ERR({e}): Exception error!") # Generic error message
                return markdown # Consider more specific error handling or logging

        return markdown

    # PYLINT_COMMENT: plugin.py:355:4: W0221: Number of parameters was 2 in 'BasePlugin.on_post_page' and is now 4 in overriding 'MkdocsWithConfluence.on_post_page' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Check `BasePlugin` for `on_post_page`'s signature. MkDocs standard is `on_post_page(self, output, page, config)`. Similar reasoning as `on_nav`.
    # PYLINT_COMMENT: Why: Method signature consistency.
    def on_post_page(self, output, page, config):
        site_dir = config.get("site_dir")
        attachments = self.page_attachments.get(page.title, [])

        if self.config["debug"]:
            print(f"\nDEBUG     - UPLOADING ATTACHMENTS TO CONFLUENCE FOR {page.title}, DETAILS:")
            print(f"FILES: {attachments}   \n")
        for attachment in attachments:
            if self.config["debug"]:
                print(f"DEBUG     - looking for {attachment} in {site_dir}")
            for p_path in Path(site_dir).rglob(f"*{attachment}"): # Renamed 'p'
                self.add_or_update_attachment(page.title, p_path)
        return output

    # PYLINT_COMMENT: plugin.py:369:4: W0221: Number of parameters was 3 in 'BasePlugin.on_page_content' and is now 5 in overriding 'MkdocsWithConfluence.on_page_content' method (arguments-differ)
    # PYLINT_COMMENT: How to fix: Check `BasePlugin` for `on_page_content`'s signature. MkDocs standard is `on_page_content(self, html, page, config, files)`. Similar reasoning.
    # PYLINT_COMMENT: Why: Method signature consistency.
    def on_page_content(self, html, page, config, files):
        return html

    def __get_page_url(self, section):
        return re.search("url='(.*)'\\)", section).group(1)[:-1] + ".md"

    def __get_page_name(self, section):
        return os.path.basename(re.search("url='(.*)'\\)", section).group(1)[:-1])

    def __get_section_name(self, section):
        if self.config["debug"]:
            print(f"DEBUG     - SECTION name: {section}")
        return os.path.basename(re.search("url='(.*)'\\/", section).group(1)[:-1])

    def __get_section_title(self, section):
        if self.config["debug"]:
            print(f"DEBUG     - SECTION title: {section}")
        try:
            r_match = re.search("Section\\(title='(.*)'\\)", section) # Renamed 'r'
            return r_match.group(1)
        except AttributeError:
            name = self.__get_section_name(section)
            print(f"WRN     - Section '{name}' doesn't exist in the mkdocs.yml nav section!")
            return name

    def __get_page_title(self, section):
        try:
            r_match = re.search("\\s*Page\\(title='(.*)',", section) # Renamed 'r'
            return r_match.group(1)
        except AttributeError:
            name = self.__get_page_url(section) # This gets URL, not just name. Consider self.__get_page_name(section) if consistent.
            print(f"WRN     - Page '{name}' doesn't exist in the mkdocs.yml nav section!")
            return name # Returns full URL path as title if not found.

    # PYLINT_COMMENT: plugin.py:404:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add a docstring, e.g., """Calculates the SHA1 hash of a file."""
    # PYLINT_COMMENT: Why: Explains what the method does.
    def get_file_sha1(self, file_path):
        hash_sha1 = hashlib.sha1()
        with open(file_path, "rb") as f_in: # Renamed 'f'
            for chunk in iter(lambda: f_in.read(4096), b""):
                hash_sha1.update(chunk)
        return hash_sha1.hexdigest()

    def add_or_update_attachment(self, page_name, filepath):
        print(f"INFO     - Mkdocs With Confluence * {page_name} *ADD/Update ATTACHMENT if required* {filepath}")
        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Add Attachment: PAGE NAME: {page_name}, FILE: {filepath}")
        page_id = self.find_page_id(page_name)
        if page_id:
            file_hash = self.get_file_sha1(filepath)
            attachment_message = f"MKDocsWithConfluence [v{file_hash}]"
            existing_attachment = self.get_attachment(page_id, filepath)
            if existing_attachment:
                file_hash_regex = re.compile(r"\[v([a-f0-9]{40})]$")
                existing_match = file_hash_regex.search(existing_attachment["version"]["message"])
                if existing_match is not None and existing_match.group(1) == file_hash:
                    if self.config["debug"]:
                        print(f" * Mkdocs With Confluence * {page_name} * Existing attachment skipping * {filepath}")
                else:
                    self.update_attachment(page_id, filepath, existing_attachment, attachment_message)
            else:
                self.create_attachment(page_id, filepath, attachment_message)
        else:
            if self.config["debug"]:
                print("PAGE DOES NOT EXISTS")

    # PYLINT_COMMENT: plugin.py:434:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add a docstring, e.g., """Retrieves attachment details from a Confluence page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    # PYLINT_COMMENT: plugin.py:434:4: R1710: Either all return statements in a function should return an expression, or none of them should. (inconsistent-return-statements)
    # PYLINT_COMMENT: How to fix: Ensure all paths return a value or all return None implicitly. If `response_json["size"]` is false or 0, it implicitly returns None. Add an explicit `return None` at the end or after the if block for clarity if that's the intention.
    # PYLINT_COMMENT: Why: Consistent return behavior makes functions easier to use correctly.
    def get_attachment(self, page_id, filepath):
        name = os.path.basename(filepath)
        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Get Attachment: PAGE ID: {page_id}, FILE: {filepath}")

        url = self.config["host_url"] + "/rest/api/content/" + page_id + "/child/attachment" # Added /rest/api/content for typical Confluence Cloud API
        headers = {"X-Atlassian-Token": "no-check"}
        if self.config["debug"]:
            print(f"URL: {url}")

        r = self.session.get(url, headers=headers, params={"filename": name, "expand": "version"})
        r.raise_for_status()
        with nostdout(): # Consider if this is necessary or if logging level can control requests' verbosity.
            response_json = r.json()
        if response_json.get("size", 0) > 0 and response_json.get("results"): # Made .get more robust
            return response_json["results"][0]
        return None # Explicit return None

    # PYLINT_COMMENT: plugin.py:451:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Updates an existing attachment on a Confluence page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def update_attachment(self, page_id, filepath, existing_attachment, message):
        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Update Attachment: PAGE ID: {page_id}, FILE: {filepath}")

        url = self.config["host_url"] + "/rest/api/content/" + page_id + "/child/attachment/" + existing_attachment["id"] + "/data"
        headers = {"X-Atlassian-Token": "no-check"}

        if self.config["debug"]:
            print(f"URL: {url}")

        filename = os.path.basename(filepath)

        # PYLINT_COMMENT: plugin.py:464:22: W0612: Unused variable 'encoding' (unused-variable)
        # PYLINT_COMMENT: How to fix: Remove `, encoding` if it's not used: `content_type, _ = mimetypes.guess_type(filepath)` or `content_type = mimetypes.guess_type(filepath)[0]`.
        # PYLINT_COMMENT: Why: Avoids clutter from unused variables.
        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = "application/octet-stream" # More specific than multipart/form-data for a single file
        # PYLINT_COMMENT: plugin.py:467:36: R1732: Consider using 'with' for resource-allocating operations (consider-using-with)
        # PYLINT_COMMENT: How to fix: Use `with open(Path(filepath), "rb") as file_to_upload:` and then use `file_to_upload` in the files dict.
        # PYLINT_COMMENT: Why: Ensures the file is properly closed after the request, even if errors occur.
        files = {"file": (filename, open(Path(filepath), "rb"), content_type), "comment": (None, message)} # Ensure comment is sent as multipart

        if not self.dryrun:
            r = self.session.post(url, headers=headers, files=files)
            r.raise_for_status() # This will raise for non-2xx.
            # The print(r.json()) and status code check below are somewhat redundant if raise_for_status() is used.
            # print(r.json()) # This might fail if response is not JSON or empty.
            if r.status_code == 200: # Should be covered by raise_for_status
                print("OK!")
            else:
                print("ERR!") # Unlikely to be reached if raise_for_status is active.

    # PYLINT_COMMENT: plugin.py:478:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Creates a new attachment on a Confluence page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def create_attachment(self, page_id, filepath, message):
        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Create Attachment: PAGE ID: {page_id}, FILE: {filepath}")

        url = self.config["host_url"] + "/rest/api/content/" + page_id + "/child/attachment"
        headers = {"X-Atlassian-Token": "no-check"}

        if self.config["debug"]:
            print(f"URL: {url}")

        filename = os.path.basename(filepath)

        # PYLINT_COMMENT: plugin.py:491:22: W0612: Unused variable 'encoding' (unused-variable)
        # PYLINT_COMMENT: How to fix: Remove `, encoding` (as above).
        # PYLINT_COMMENT: Why: Avoids unused variables.
        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None:
            content_type = "application/octet-stream"
        # PYLINT_COMMENT: plugin.py:494:36: R1732: Consider using 'with' for resource-allocating operations (consider-using-with)
        # PYLINT_COMMENT: How to fix: Use `with open(filepath, "rb") as file_to_upload:`.
        # PYLINT_COMMENT: Why: Proper file resource management.
        files = {"file": (filename, open(filepath, "rb"), content_type), "comment": (None, message)}
        if not self.dryrun:
            r = self.session.post(url, headers=headers, files=files)
            # print(r.json()) # Can fail if not JSON.
            r.raise_for_status()
            if r.status_code == 200: # Covered by raise_for_status
                print("OK!")
            else:
                print("ERR!") # Unlikely reached.

    # PYLINT_COMMENT: plugin.py:504:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Finds the Confluence page ID for a given page name and space."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def find_page_id(self, page_name):
        if self.config["debug"]:
            print(f"INFO     -    * Mkdocs With Confluence: Find Page ID: PAGE NAME: {page_name}")
        # Proper URL encoding for parameters is better handled by requests' `params` argument.
        # name_confl = page_name.replace(" ", "+") # Better: use requests params
        # url = self.config["host_url"] + "?title=" + name_confl + "&spaceKey=" + self.config["space"] + "&expand=history"
        url = self.config["host_url"] + "/rest/api/content" # Base endpoint for content
        params = {
            "title": page_name,
            "spaceKey": self.config["space"],
            "expand": "history"
        }
        if self.config["debug"]:
            print(f"URL: {url}, PARAMS: {params}")
        r = self.session.get(url, params=params)
        r.raise_for_status()
        with nostdout():
            response_json = r.json()
        if response_json.get("results"): # More robust check
            if self.config["debug"]:
                print(f"ID: {response_json['results'][0]['id']}")
            return response_json["results"][0]["id"]
        # PYLINT_COMMENT: plugin.py:515:8: R1705: Unnecessary "else" after "return", remove the "else" and de-indent the code inside it (no-else-return)
        # PYLINT_COMMENT: How to fix: Unindent the `if self.config["debug"]:` block and the `return None`.
        # PYLINT_COMMENT: Why: If the `if response_json.get("results"):` is true, it returns. The code below it is effectively the `else` block.
        else: # This 'else' can be removed and the following code unindented.
            if self.config["debug"]:
                print("PAGE DOES NOT EXIST")
            return None

    # PYLINT_COMMENT: plugin.py:524:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Adds a new page to Confluence under a specific parent page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def add_page(self, page_name, parent_page_id, page_content_in_storage_format):
        print(f"INFO     -    * Mkdocs With Confluence: {page_name} - *NEW PAGE*")

        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Adding Page: PAGE NAME: {page_name}, parent ID: {parent_page_id}")
        url = self.config["host_url"] + "/rest/api/content/"
        if self.config["debug"]:
            print(f"URL: {url}")
        headers = {"Content-Type": "application/json"}
        space = self.config["space"]
        data = {
            "type": "page",
            "title": page_name,
            "space": {"key": space},
            "ancestors": [{"id": parent_page_id}], # This requires parent_page_id to be valid.
            "body": {"storage": {"value": page_content_in_storage_format, "representation": "storage"}},
        }
        if parent_page_id is None: # If no parent, cannot set ancestors. Check API for creating top-level page in space.
            del data["ancestors"] # Or handle differently based on API requirements

        if self.config["debug"]:
            print(f"DATA: {data}")
        if not self.dryrun:
            r = self.session.post(url, json=data, headers=headers)
            r.raise_for_status()
            if r.status_code == 200: # Covered by raise_for_status
                if self.config["debug"]:
                    print("OK!")
            else: # Unlikely reached
                if self.config["debug"]:
                    print("ERR!")

    # PYLINT_COMMENT: plugin.py:553:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Updates an existing page in Confluence."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def update_page(self, page_name, page_content_in_storage_format):
        page_id = self.find_page_id(page_name)
        print(f"INFO     -    * Mkdocs With Confluence: {page_name} - *UPDATE*")
        if self.config["debug"]:
            print(f" * Mkdocs With Confluence: Update PAGE ID: {page_id}, PAGE NAME: {page_name}")
        if page_id:
            page_version = self.find_page_version(page_name)
            if page_version is None: # Should not happen if page_id was found, but good to be safe
                if self.config["debug"]: print(f"ERR! Could not find version for page {page_name} (ID: {page_id})")
                return
            page_version = page_version + 1
            url = self.config["host_url"] + "/rest/api/content/" + page_id
            if self.config["debug"]:
                print(f"URL: {url}")
            headers = {"Content-Type": "application/json"}
            space = self.config["space"] # Not usually needed for PUT by ID, but doesn't hurt if API ignores.
            data = {
                "id": page_id,
                "title": page_name,
                "type": "page",
                "space": {"key": space}, # May not be required for update by ID
                "body": {"storage": {"value": page_content_in_storage_format, "representation": "storage"}},
                "version": {"number": page_version},
            }

            if not self.dryrun:
                r = self.session.put(url, json=data, headers=headers)
                r.raise_for_status()
                if r.status_code == 200: # Covered by raise_for_status
                    if self.config["debug"]:
                        print("OK!")
                else: # Unlikely reached
                    if self.config["debug"]:
                        print("ERR!")
        else:
            if self.config["debug"]:
                print("PAGE DOES NOT EXIST YET!")

    # PYLINT_COMMENT: plugin.py:588:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Finds the current version number of a Confluence page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def find_page_version(self, page_name):
        if self.config["debug"]:
            print(f"INFO     -    * Mkdocs With Confluence: Find PAGE VERSION, PAGE NAME: {page_name}")
        # name_confl = page_name.replace(" ", "+")
        # url = self.config["host_url"] + "?title=" + name_confl + "&spaceKey=" + self.config["space"] + "&expand=version"
        url = self.config["host_url"] + "/rest/api/content"
        params = {
            "title": page_name,
            "spaceKey": self.config["space"],
            "expand": "version"
        }
        r = self.session.get(url, params=params)
        r.raise_for_status()
        with nostdout():
            response_json = r.json()
        # PYLINT_COMMENT: The check `if response_json["results"] is not None:` is okay, but `if response_json.get("results"):` is safer.
        if response_json.get("results"): # Check if results list is not empty
            if self.config["debug"]:
                print(f"VERSION: {response_json['results'][0]['version']['number']}")
            return response_json["results"][0]["version"]["number"]
        # PYLINT_COMMENT: plugin.py:597:8: R1705: Unnecessary "else" after "return", remove the "else" and de-indent the code inside it (no-else-return)
        # PYLINT_COMMENT: How to fix: Unindent the `if self.config["debug"]:` block and `return None`.
        # PYLINT_COMMENT: Why: If the `if` condition is true, it returns; otherwise, the subsequent code is executed (effectively the else).
        else:
            if self.config["debug"]:
                print("PAGE DOES NOT EXISTS")
            return None

    # PYLINT_COMMENT: plugin.py:606:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Finds the title of the immediate parent of a Confluence page."""
    # PYLINT_COMMENT: Why: Explains functionality.
    def find_parent_name_of_page(self, name):
        if self.config["debug"]:
            print(f"INFO     -    * Mkdocs With Confluence: Find PARENT OF PAGE, PAGE NAME: {name}")
        idp = self.find_page_id(name)
        if not idp: # If page itself doesn't exist, it has no parent.
            if self.config["debug"]: print(f"Page '{name}' not found, so cannot find its parent.")
            return None
        url = self.config["host_url"] + "/rest/api/content/" + idp + "?expand=ancestors"

        r = self.session.get(url)
        r.raise_for_status()
        with nostdout():
            response_json = r.json()
        if response_json and response_json.get("ancestors"): # Check if ancestors list exists and is not empty
            if self.config["debug"]:
                print(f"PARENT NAME: {response_json['ancestors'][-1]['title']}")
            return response_json["ancestors"][-1]["title"]
        # PYLINT_COMMENT: plugin.py:616:8: R1705: Unnecessary "else" after "return", remove the "else" and de-indent the code inside it (no-else-return)
        # PYLINT_COMMENT: How to fix: Unindent the `if self.config["debug"]:` block and `return None`.
        # PYLINT_COMMENT: Why: Same reasoning as above.
        else:
            if self.config["debug"]:
                print("PAGE DOES NOT HAVE PARENT or ancestors list is empty")
            return None

    # PYLINT_COMMENT: plugin.py:625:4: C0116: Missing function or method docstring (missing-function-docstring)
    # PYLINT_COMMENT: How to fix: Add docstring, e.g., """Waits for a condition to become truthy or a timeout occurs."""
    # PYLINT_COMMENT: Note: The 'condition' parameter as used in on_page_markdown is a value, not a callable. This method currently waits if the initial value of 'condition' is falsey. It does not re-evaluate anything.
    # PYLINT_COMMENT: How to fix (usage): If the intent is to wait for `find_page_id` to return a value, the loop should be `while self.find_page_id(page_name) is None and time.time() - start < timeout:`.
    # PYLINT_COMMENT: Why: The current implementation of `wait_until` might not work as intended for waiting for an external state to change.
    def wait_until(self, condition, interval=0.1, timeout=1):
        start = time.time()
        # If condition is a value (e.g. an ID or None):
        # If initially None (falsey), it will sleep. If initially an ID (truthy), it won't sleep.
        # It does not re-check or poll for the condition to change here. That happens outside this method.
        while not condition and time.time() - start < timeout:
            time.sleep(interval)
        # To make it a true polling wait:
        # `condition` should be a callable: `while not condition_callable() and time.time() - start < timeout:`
