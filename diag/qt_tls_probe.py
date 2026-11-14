"""Probe Qt6 TLS / proxy behaviour inside FreeCAD's own Python+Qt environment.

Run with: F:\FreeCAD\bin\python.exe D:\E\Model\diag\qt_tls_probe.py
"""
import os
import sys

from PySide6 import QtCore, QtNetwork

print("Qt version:", QtCore.qVersion())
print("supportsSsl:", QtNetwork.QSslSocket.supportsSsl())
try:
    print("availableBackends:", QtNetwork.QSslSocket.availableBackends())
except Exception as exc:  # pragma: no cover
    print("availableBackends: <unavailable>", exc)
try:
    print("activeBackend:", QtNetwork.QSslSocket.activeBackend())
except Exception as exc:  # pragma: no cover
    print("activeBackend: <unavailable>", exc)
try:
    print("sslLibraryBuildVersionString:", QtNetwork.QSslSocket.sslLibraryBuildVersionString())
except Exception as exc:  # pragma: no cover
    print("sslLibraryBuildVersionString: <unavailable>", exc)

app = QtCore.QCoreApplication([])

# Report the system proxy the way FreeCAD's NetworkManager resolves it
query = QtNetwork.QNetworkProxyQuery(QtCore.QUrl("https://github.com/FreeCAD/FreeCAD"))
try:
    proxies = QtNetwork.QNetworkProxyFactory.systemProxyForQuery(query)
    print("systemProxyForQuery(github):", [(p.type().name, p.hostName(), p.port()) for p in proxies])
except Exception as exc:
    print("systemProxyForQuery failed:", exc)

query2 = QtNetwork.QNetworkProxyQuery(QtCore.QUrl("https://addons.freecad.org/status"))
try:
    proxies2 = QtNetwork.QNetworkProxyFactory.systemProxyForQuery(query2)
    print("systemProxyForQuery(addons):", [(p.type().name, p.hostName(), p.port()) for p in proxies2])
except Exception as exc:
    print("systemProxyForQuery(addons) failed:", exc)


def fetch(url, mode):
    """mode: system | none"""
    mgr = QtNetwork.QNetworkAccessManager()
    if mode == "system":
        QtNetwork.QNetworkProxyFactory.setUseSystemConfiguration(True)
        q = QtNetwork.QNetworkProxyQuery(QtCore.QUrl(url))
        res = QtNetwork.QNetworkProxyFactory.systemProxyForQuery(q)
        if res and res[0]:
            mgr.setProxy(res[0])
    else:
        mgr.setProxy(QtNetwork.QNetworkProxy(QtNetwork.QNetworkProxy.NoProxy))
    req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
    req.setHeader(QtNetwork.QNetworkRequest.UserAgentHeader, "FreeCAD-Diagnostic/1.0")
    reply = mgr.get(req)
    loop = QtCore.QEventLoop()

    def done():
        loop.quit()

    reply.finished.connect(done)
    reply.sslErrors.connect(lambda errs: print("   sslErrors:", [e.errorString() for e in errs]))
    QtCore.QTimer.singleShot(30000, loop.quit)
    loop.exec()
    print(f"[{mode}] {url}")
    print("   error:", reply.error(), reply.errorString())
    print("   http status:", reply.attribute(QtNetwork.QNetworkRequest.HttpStatusCodeAttribute))
    body = bytes(reply.readAll())
    print("   bytes:", len(body), body[:80])
    reply.deleteLater()


for mode in ("none", "system"):
    for url in ("https://addons.freecad.org/status", "https://github.com"):
        fetch(url, mode)
        app.processEvents()

print("done")
