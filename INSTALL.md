# ---  INSTALL for Claudia  ---

To install Claudia, simply run as usual: <br/>
`$ make` <br/>
`$ [sudo] make install`

You can run the tools without installing them, by using instead: <br/>
<i>(Replace '&lt;tool&gt;' by a proper name, in lowercase. Some distros may need to use 'python' here)</i> <br/>
`$ make` <br/>
`$ python3 src/<tool>.py`

Packagers can make use of the 'PREFIX' and 'DESTDIR' variable during install, like this: <br/>
`$ make install PREFIX=/usr DESTDIR=./test-dir`

<br/>

Use LRELEASE variable if case lrelease binary is not in PATH.

===== BUILD DEPENDENCIES =====
--------------------------------
The required build dependencies are: <i>(devel packages of these)</i>

 - Qt5
 - PyQt5 (Py3 version)

On Debian and Ubuntu, use these commands to install all build dependencies: <br/>
`$ sudo apt-get install qtbase5-dev qtbase5-dev-tools` <br/>
`$ sudo apt-get install python3-pyqt5 python3-pyqt5.qtsvg pyqt5-dev-tools`

===== RUNTIME DEPENDENCIES =====
----------------------------------
All tools require Python3 and Qt5 (PyQt5). <br/>
Here's the required run-time dependencies of each of the main tools:

Claudia requires jackdbus and ladish <br/>
Recommends a2jmidid <br/>

To run Claudia you'll additionally need:

 - python3-dbus
 - python3-dbus.mainloop.qt

Optional:

 - a2jmidid
