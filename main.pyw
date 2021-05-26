import os
import sys
import codecs
import hashlib

from PyQt5.QtWidgets import (QApplication, QGridLayout, QWidget, QComboBox,
                             QMainWindow, QStatusBar, QToolBar, QLineEdit,
                             QFileDialog, QLabel, QShortcut, QTextEdit,
                             QDialog, QVBoxLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeySequence

from lxml import etree
from lxml.etree import XMLSyntaxError

avaliacao = ['10102019', '00020010', '50000349', '50000144', '00010929',
             '60030070', '10101222', '90050215']


class MainWindow(QMainWindow):
    def __init__(self, parent=None, dropfile=None):
        super().__init__(parent)

        open_shortcut = QShortcut(QKeySequence(self.tr("Ctrl+O")), self)
        open_shortcut.activated.connect(self.fileSelect)

        self.setWindowTitle("Validador TISS")
        self.resize(800, 600)
        self.setAcceptDrops(True)
        self._addWidgets()
        self._createMenu()
        self._createStatusBar()
        self._createToolbar()
        self.show()
        if dropfile:
            self._filepath.setText(dropfile)
            try:
                self.readXML()
            except XMLSyntaxError:
                self._filepath.setText("")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            path = e.mimeData().urls()[0].path()[1:]
            if path.endswith('.xml'):
                e.accept()
            else:
                e.ignore()
        else:
            e.ignore()

    def dropEvent(self, e):
        path = e.mimeData().urls()[0].path()[1:]
        self._filepath.setText(path)
        self._mainWidget.validate()

    def _createMenu(self):
        self.menu = self.menuBar().addMenu("&Menu")
        self.menu.addAction('&Selecionar', self.fileSelect)
        self.menu.addAction('&Validar', self._mainWidget.validate)
        self.menu.addAction('&Fechar', self.close)

    def _addWidgets(self):
        self._filepath = QLineEdit(self)
        self._convenios = QComboBox(self)
        self._populateComboBox()

        self._mainWidget = MainWidget(self)
        self.setCentralWidget(self._mainWidget)
        
    def _populateComboBox(self):
        convenios = os.listdir('xsd Convênios/')
        convenios = [x.split('.')[0] for x in convenios if x.endswith('.xsd')]
        convenios = ["Selecionar"] + convenios
        self._convenios.addItems(convenios)

    def _createStatusBar(self):
        self.status = QStatusBar()
        self.setStatusBar(self.status)

    def _createToolbar(self):
        tools = QToolBar()
        self.addToolBar(tools)
        tools.setMovable(False)
        tools.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        tools.addAction('Selecionar', self.fileSelect)
        tools.addAction('Validar', self._mainWidget.validate)
        tools.addWidget(self._filepath)
        tools2 = QToolBar()
        self.addToolBarBreak()
        self.addToolBar(tools2)
        tools2.setMovable(False)
        tools2.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        tools2.addWidget(QLabel('Convênio:'))
        tools2.addWidget(self._convenios)

    def fileSelect(self):
        dlg = QFileDialog()
        dlg.ExistingFile
        dlg.setAcceptMode(QFileDialog.AcceptOpen)
        filepath = dlg.getOpenFileName(
            self, self.tr("Selecione o arquivo XML"), "",
            self.tr("Arquivos XML (*.xml)")
        )
        if filepath[0]:
            self._filepath.setText(filepath[0])
            self._mainWidget.validate()

    def getFilePath(self):
        return self._filepath.text()


class MainWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.layout = QGridLayout(self)
        self.xmlversion = QLabel('Versão do XML: ')
        self.validation = QTextEdit()
        self.validation.setReadOnly(True)
        self._addWidgets()
        self.show()

    def _addWidgets(self):
        self.layout.addWidget(self.xmlversion, 0, 0)
        self.layout.addWidget(self.validation, 1, 0, 1, 2)

        self.setLayout(self.layout)
        
    def schemaValidation(self, doc, schema, versao, namespace, tag_guia):
        for error in schema.error_log:
            translated = error.message.replace(
                "{http://www.ans.gov.br/padroes/tiss/schemas}", '')
            if error.type != 1824 and "guia" in error.path:
                if versao.startswith("3"):
                    guia = error.path.split("/")[2:6]
                else:
                    guia = error.path.split("/")[2:7]
                guia = "/" + "/".join(guia)
                guia = doc.find(guia, namespaces=namespace)
                guia = guia.find(tag_guia).text
                self.validation.append(
                    "Erro encontrado na linha %i (Guia: %s). %s\r\n"
                    % (error.line, guia, translated)
                    )
            else:
                self.validation.append(f"Erro: {translated}")

    def validate(self):
        try:
            doc = etree.parse(self.parent.getFilePath())
        except OSError:
            ErrorDialog(self)
            return
        except XMLSyntaxError:
            ErrorDialog(self)
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        root = doc.getroot()
        tiss_v = root.attrib.values()[0].split('/')[-1]
        versao = tiss_v[5:12].replace('_', '.')
        ans_namespace = {"ans": "http://www.ans.gov.br/padroes/tiss/schemas"}
        self.xmlversion.setText(f"Versão do XML identificada: {versao}")
        self.validation.setText("")
        if versao.startswith("3"):
            _guia = doc.findall("//{*}guiaSP-SADT")
            tag_guia = "{*}cabecalhoGuia/{*}numeroGuiaPrestador"
        else:
            _guia = doc.findall("//{*}guiaSP_SADT")
            tag_guia = "{*}identificacaoGuiaSADTSP/{*}numeroGuiaPrestador"

        try:
            schema_root = etree.parse("xsd/%s" % tiss_v)
        except OSError:
            self.validation.append(
                "Validação XML indisponível para essa versão!\n"
            )
            QApplication.restoreOverrideCursor()
            return

        schema = etree.XMLSchema(schema_root)
        schema.validate(doc)
        self.schemaValidation(doc, schema, versao, ans_namespace, tag_guia)

        ANS = doc.find("//{*}registroANS").text
        for guia in _guia:
            n = guia.find(tag_guia).text
            _proc = guia.findall(
                "{*}procedimentosExecutados/"
                "{*}procedimentoExecutado"
            )
            prev_proc = 0
            data = None
            for proc in _proc:
                if (proc == prev_proc) and (prev_proc in avaliacao):
                    self.validation.append(f"Guia {n}:Avaliação duplicada\n")
                if (proc == prev_proc) and (ANS == "346659"):
                    if data == proc.find("{*}dataExecucao").text:
                        self.validation.append(f"Guia {n}:"
                                               "Possível duplicidade\n")
                data = proc.find("{*}dataExecucao").text
                qtd = float(proc.find("{*}quantidadeExecutada").text)
                unit = float(proc.find("{*}valorUnitario").text)
                total = float(proc.find("{*}valorTotal").text)
                if round(qtd*unit, 2) != total:
                    self.validation.append(
                        f"Guia {n}:Valor total diferente do calculado\n"
                    )
                prev_proc = proc
                
        if self.parent._convenios.currentIndex() != 0:
            convenio = self.parent._convenios.currentText()
            schema_root = etree.parse(f'xsd Convênios/{convenio}.xsd')
            schema = etree.XMLSchema(schema_root)
            schema.validate(doc)
            self.schemaValidation(doc, schema, versao, ans_namespace, tag_guia)
            
                
        if ANS == '346659':
            datas = doc.findall("//{*}dataExecucao")
            for data in datas:
                parent = data.getparent()
                if parent.find("{*}horaInicial") is None:
                    hora_inicial = etree.Element(f"{ans_namespace['ans']}horaInicial")
                    hora_inicial.text = "07:00:00"
                    hora_final = etree.Element(f"{ans_namespace['ans']}horaFinal")
                    hora_final.text = "07:45:00"
                    parent.insert(parent.index(data) + 1, hora_final)
                    parent.insert(parent.index(data) + 1, hora_inicial)

        # if schema.error_log:
        #     QApplication.restoreOverrideCursor()
        #     return 0

        docstr = ''
        for e in doc.iter():
            if e.tag != '{http://www.ans.gov.br/padroes/tiss/schemas}hash':
                if e.text.strip() != '':
                    docstr = docstr + e.text.strip()
            else:
                calchash = hashlib.md5(docstr.encode()).hexdigest().upper()
        if e.text.upper() != calchash:
            self.validation.append(
                f"Hash incorreto!\nHash encontrado: {e.text.upper()}\n"
                f"Hash calculado: {calchash}\n"
                "Hash incorreto corrigido!\n"
            )
            e.text = calchash
            encoding = doc.docinfo.encoding
            with codecs.open(self.parent.getFilePath(), "w",
                      encoding=encoding) as f:
                f.write(etree.tostring(doc, xml_declaration=True,
                                       encoding=encoding) \
                        .decode(encoding=encoding))
        self.validation.append("Validação concluída!")
        QApplication.restoreOverrideCursor()


class ErrorDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('Arquivo inválido!')
        self.setModal(True)
        self.text = QLabel('O arquivo selecionado não é válido!')
        self.button = QDialogButtonBox(QDialogButtonBox.Ok)
        self.button.accepted.connect(self.accept)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.text)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.exec_()


if __name__ == '__main__':
    dropfile = sys.argv[1] if len(sys.argv) > 1 else None
    app = QApplication([])
    window = MainWindow(None, dropfile)
    window.show()
    app.exec_()
    QApplication.restoreOverrideCursor()
