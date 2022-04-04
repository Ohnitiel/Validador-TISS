import os
import sys
import codecs
import hashlib

from PyQt5.QtWidgets import (QApplication, QGridLayout, QWidget, QComboBox,
                             QMainWindow, QStatusBar, QToolBar, QLineEdit,
                             QFileDialog, QLabel, QShortcut, QTextEdit,
                             QDialog, QVBoxLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, QThreadPool, pyqtSignal, QThread
from PyQt5.QtGui import QKeySequence

from lxml import etree
from lxml.etree import XMLSyntaxError
from deep_translator import GoogleTranslator


avaliacao = ['10102019', '00020010', '50000349', '50000144', '00010929',
             '60030070', '10101222', '90050215']

convenios_senha = ['AMIL', 'CASSI', 'GAMA', 'SAÚDE BRB', 'SLAM']

translator = GoogleTranslator(source='en', target='pt')

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
            try:
                self._mainWidget.validate()
            except Exception as e:
                self._mainWidget.validation.clear()
                self._mainWidget.validation.append(f'Erro: {e}')

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
        self.ThreadPool = QThreadPool()
        self.worker = Worker(self)

    def _addWidgets(self):
        self.layout.addWidget(self.xmlversion, 0, 0)
        self.layout.addWidget(self.validation, 1, 0, 1, 2)

        self.setLayout(self.layout)

    def validate(self):
        self.validation.setText("")
        try:
            self.worker.start()
        except Exception as e:
            self.validation.setText(f'{e}')

    def signals(self, text):
        self.validation.append(text)

    def getFilePath(self):
        return self.parent.getFilePath()

    def getSelectedItemText(self):
        return self.parent._convenios.currentText()

    def getSelectedItemIndex(self):
        return self.parent._convenios.currentIndex()


class Worker(QThread):
    edit = pyqtSignal(str)

    def __init__(self, parent):
        QThread.__init__(self)
        self.parent = parent
        self.edit.connect(self.parent.signals)

    def getSelectedItemText(self):
        return self.parent.getSelectedItemText()

    def getSelectedItemIndex(self):
        return self.parent.getSelectedItemIndex()

    def run(self):
        try:
            doc = etree.parse(self.parent.getFilePath())
        except OSError:
            ErrorDialog(self.parent)
            return
        except XMLSyntaxError:
            ErrorDialog(self.parent)
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)

        ans_namespace = {"ans": "http://www.ans.gov.br/padroes/tiss/schemas"}

        root = doc.getroot()
        tiss_v = root.attrib.values()[0].split('/')[-1]
        versao = tiss_v[5:12].replace('_', '.')

        self.parent.xmlversion.setText(f"Versão do XML identificada: {versao}")
        if versao.startswith("3"):
            _guia = doc.findall("//{*}guiaSP-SADT")
            tag_guia = "{*}cabecalhoGuia/{*}numeroGuiaPrestador"
        else:
            _guia = doc.findall("//{*}guiaSP_SADT")
            tag_guia = "{*}identificacaoGuiaSADTSP/{*}numeroGuiaPrestador"

        try:
            schema_root = etree.parse("xsd/%s" % tiss_v)
        except OSError:
            self.edit.emit("Validação XML indisponível para essa versão!\n")
            QApplication.restoreOverrideCursor()
            return

        if self.getSelectedItemText() == 'TST':
            cdTables = doc.findall("//{*}codigoTabela")
            for i in cdTables:
                i.text = '22'

        if doc.find("//{*}tipoTransacao").text == "RECURSO_GLOSA":
            doc = self.recursoGlosaValidation(doc)

        schema = etree.XMLSchema(schema_root)
        schema.validate(doc)
        self.schemaValidation(doc, schema, versao, ans_namespace, tag_guia)

        ANS = doc.find("//{*}registroANS").text
        for guia in _guia:
            try:
                n = guia.find(tag_guia).text
            except AttributeError:
                n = 'Sem número de guia'
            _proc = guia.findall("{*}procedimentosExecutados/{*}procedimentoExecutado")
            prev_proc = 0
            data = None
            for proc in _proc:
                if (proc == prev_proc) and (prev_proc in avaliacao):
                    self.edit.append(f"Guia {n}:Avaliação duplicada\n")
                if (proc == prev_proc) and (ANS == "346659"):
                    if data == proc.find("{*}dataExecucao").text:
                        self.edit.emit(
                            f"Guia {n}: Possível duplicidade de procedimentos!\n")
                data = proc.find("{*}dataExecucao").text
                qtd = float(proc.find("{*}quantidadeExecutada").text)
                unit = float(proc.find("{*}valorUnitario").text)
                total = float(proc.find("{*}valorTotal").text)
                if round(qtd*unit, 2) != total:
                    self.edit.emit(
                        f"Guia {n}:Valor total diferente do calculado\n")
                prev_proc = proc

        if self.getSelectedItemIndex() != 0:
            convenio = self.getSelectedItemText()
            schema_root = etree.parse(f'xsd Convênios/{convenio}.xsd')
            schema = etree.XMLSchema(schema_root)
            schema.validate(doc)
            self.schemaValidation(doc, schema, versao, ans_namespace, tag_guia)

        if ANS == '346659':
            doc = self.cassiValidation(doc, ans_namespace)
        if ANS == '358509':
            doc = self.slamValidation(doc)

        if self.getSelectedItemText() in convenios_senha:
            guias = doc.findall("//{*}guiaSP-SADT")
            for guia in guias:
                guia_n = guia.find(
                    "{*}cabecalhoGuia/{*}numeroGuiaPrestador").text
                try:
                    guia.find("{*}dadosAutorizacao/{*}senha").text
                except AttributeError:
                    self.edit.emit(f"Guia Nº {guia_n} sem senha!\n")

        docstr = ''
        for e in doc.iter():
            if e.tag != '{http://www.ans.gov.br/padroes/tiss/schemas}hash':
                if e.text.strip() != '':
                    docstr = docstr + e.text.strip()
            else:
                calchash = hashlib.md5(docstr.encode()).hexdigest().upper()
        if e.text.upper() != calchash:
            self.edit.emit(
                f"Hash incorreto!\nHash encontrado: {e.text.upper()}\n"
                f"Hash calculado: {calchash}\n"
                "Hash incorreto corrigido!\n"
            )
            e.text = calchash
            encoding = doc.docinfo.encoding
            with codecs.open(self.parent.getFilePath(), "w",
                             encoding=encoding) as f:
                f.write(etree.tostring(doc, xml_declaration=True,
                                       encoding=encoding)
                        .decode(encoding=encoding))
        self.edit.emit("Validação concluída!")
        QApplication.restoreOverrideCursor()

    def schemaValidation(self, doc, schema, versao, namespace, tag_guia):
        for error in schema.error_log:
            msg = error.message.replace(
                "{http://www.ans.gov.br/padroes/tiss/schemas}", '')
            translated = translator.translate(msg)
            if error.type != 1824 and "guia" in error.path:
                if versao.startswith("3"):
                    guia = error.path.split("/")[2:6]
                else:
                    guia = error.path.split("/")[2:7]
                guia = "/" + "/".join(guia)
                guia = doc.find(guia, namespaces=namespace)
                try:
                    guia = guia.find(tag_guia).text
                except AttributeError:
                    guia = "Sem número de guia"
                self.edit.emit(
                    "Erro encontrado na linha %i (Guia: %s). %s\r\n"
                    % (error.line, guia, translated)
                )
            else:
                self.edit.emit(f"Erro: {translated}")

    def cassiValidation(self, doc, ans_namespace):
        datas = doc.findall("//{*}dataExecucao")
        for data in datas:
            parent = data.getparent()
            if parent.find("{*}horaInicial") is None:
                hora_inicial = etree.Element(etree.QName(
                    ans_namespace['ans'], 'horaInicial'))
                hora_inicial.text = "07:00:00"
                hora_final = etree.Element(etree.QName(
                    ans_namespace['ans'], 'horaFinal'))
                hora_final.text = "07:45:00"
                parent.insert(parent.index(data) + 1, hora_final)
                parent.insert(parent.index(data) + 1, hora_inicial)
        return doc

    def slamValidation(self, doc):
        dados = doc.findall("//{*}dadosAutorizacao")
        for dado in dados:
            guia = dado.getparent().find(
                "{*}cabecalhoGuia/{*}numeroGuiaPrestador")
            if dado.find("{*}numeroGuiaOperadora") is None:
                self.edit.emit(f"{guia.text} sem número da guia na "
                                       "operadora!")
        return doc

    def recursoGlosaValidation(self, doc):
        guias = doc.findall("//{*}numeroGuiaOrigem")
        oldGuia = guias[0]
        oldOpc = oldGuia.getparent().find("{*}opcaoRecursoGuia")
        guias = guias[1:]
        for guia in guias:
            if guia.text == oldGuia.text:
                parent = guia.getparent()
                opc = parent.find("{*}opcaoRecursoGuia")
                item = opc.find("{*}itensGuia")
                opc.remove(item)
                oldOpc.append(item)
                parent.getparent().remove(parent)
            else:
                oldGuia = guia
                oldOpc = guia.getparent().find("{*}opcaoRecursoGuia")
                continue
        return doc


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
