"""Mimic FreeCAD AddonManager proxy setup exactly:
It resolves the *system* proxy using a query for https://github.com/FreeCAD/FreeCAD,
then applies that one proxy to the whole QNetworkAccessManager.
"""
import sys

from PySide6 import QtCore, QtNetwork

app = QtCore.QCoreApplication([])

print("availableBackends:", QtNetwork.QSslSocket.availableBackends())
print("activeBackend:", QtNetwork.QSslSocket.activeBackend())

q = QtNetwork.QNetworkProxyQuery(QtCore.QUrl("https://github.com/FreeCAD/FreeCAD"))
res = QtNetwork.QNetworkProxyFactory.systemProxyForQuery(q)
print("proxy resolved from github query:", [(p.type().name, p.hostName(), p.port()) for p in res])

mgr = QtNetwork.QNetworkAccessManager()
if res and res[0]:
    mgr.setProxy(res[0])
    print("applied to QNAM:", mgr.proxy().type().name, mgr.proxy().hostName(), mgr.proxy().port())


def fetch(url):
    req = QtNetwork.QNetworkRequest(QtCore.QUrl(url))
    req.setHeader(QtNetwork.QNetworkRequest.UserAgentHeader, "FreeCAD-Diagnostic/1.0")
    reply = mgr.get(req)
    loop = QtCore.QEventLoop()

    def done():
        loop.quit()

    reply.finished.connect(done)
    reply.sslErrors.connect(lambda errs: print("   sslErrors:", [e.errorString() for e in errs]))
    QtCore.QTimer.singleShot(40000, loop.quit)
    loop.exec()
    print(f"{url}")
    print("   error:", reply.error().name, "|", reply.errorString())
    print("   http status:", reply.attribute(QtNetwork.QNetworkRequest.HttpStatusCodeAttribute))
    body = bytes(reply.readAll())
    print("   bytes:", len(body), body[:60])
    reply.deleteLater()
    app.processEvents()


for url in (
    "https://addons.freecad.org/status",
    "https://addons.freecad.org/addon_catalog_cache.zip",
    "https://github.com",
):
    fetch(url)
print("done")
