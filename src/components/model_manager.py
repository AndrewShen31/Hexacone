from typing import Optional, List

from src.widgets import *
from src.interface.project_file_interface import ProjectFI
from src.components.workspace.executor import ModelExecutor
from src.components.workspace.viewport import WorkspaceScene, WorkspaceView
from constants import DEBUG__

"""
### GUI Layout (under Model Tab) ###
Model Selector  (ModelManager)
--------------------------------
Model      | Model     | Inspector
Interface  | Central   | Panel
           | Workspace |
* all 3 subsection are part of (ModelWorkspace:QWidget)
"""


class ModelWorkspace(QWidget):
	name = "Unnamed"
	key: Optional[int] = None

	nameChanged = pyqtSignal(str)
	modelUpdate = pyqtSignal("PyQt_PyObject")  # emits an update to any changes in the model workspace

	def __init__(self, proj: ProjectFI, inst_ui=True, parent=None):
		super().__init__(parent=parent)
		self.project = proj

		if inst_ui: self.inst_ui()

	def inst_ui(self, view=None):
		# Graphics Scene: Where the node will be selected
		scene = WorkspaceScene(0, 0, 1920, 1080)

		if view is None: self.view = WorkspaceView(scene)
		else: self.view = view
		# self.view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		# self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
		# self.view.setDragMode(self.view.NoDrag)

		from src.components.workspace import nodes

		m_label = QLabel("Select Nodes:")
		m_node = NodeMenu(self.view, nodes.export)

		self.b_name = QLabel(self.name)
		name_fnt = self.b_name.font()
		name_fnt.setPointSize(14)
		self.b_name.setFont(name_fnt)
		b_inp_nd = InputDialog("Set Name")  # model name input
		b_inp_nd.inputSelected.connect(lambda s: self.set_name( s, self.b_name))

		b_save_mdl = QPushButton("Save Model")  # save model
		b_save_mdl.clicked.connect(lambda checked: self.save_model())
		b_clear_mdl = QPushButton("Clear Model")
		b_clear_mdl.clicked.connect(lambda checked: self.clear_model())
		b_exec_mdl = QPushButton("Execute Model")
		b_exec_mdl.clicked.connect(lambda checked: self.execute())

		intf_menu = QVBoxLayout()  # interface menu
		intf_menu.addWidget(self.b_name)
		intf_menu.addWidget(b_inp_nd)
		intf_menu.addWidget(QHLine())
		intf_menu.addWidget(b_save_mdl)
		intf_menu.addWidget(b_clear_mdl)
		intf_menu.addWidget(b_exec_mdl)
		intf_menu.addWidget(m_label)
		intf_menu.addWidget(m_node)
		intf_menu.addStretch()

		insp_menu = QVBoxLayout()  # inspector menu
		insp_menu.addWidget(QLabel("This is the explanation menu"))

		central = QHBoxLayout()
		central.addLayout(intf_menu, 4)
		central.addWidget(self.view, 30)
		central.addLayout(insp_menu, 3)

		self.setLayout(central)

	def update_proj(self, proj: ProjectFI): self.project = proj

	def set_name(self, name: str, label: QLabel):
		if self.project is not None:
			self.project.setup()

			self.name = name
			label.setText(name)
			self.nameChanged.emit(name)

			if self.key is None:
				reg_key = self.project.get_key(name)
				if reg_key is not None:
					self.key = reg_key
				else:
					print(f"[ERROR] The model name <{name}> is currently an active name; NO DUPLICATE NAMES")
			else:
				self.project.change_name(self.key, name)
				self.project.save()
		else:
			ErrorBox(**ErrorBox.E001).exec()

	def save_model(self):
		if self.project is not None:
			if self.key is not None:
				self.project.save_mdl_exec(self.key, self.view.items())
				self.project.save_mdl_proj(self.key, self.view.items())
				self.project.save()
			else:
				ErrorBox(**ErrorBox.E008).exec()
				print("Error: Project File Interface key is empty")
		else:
			ErrorBox(**ErrorBox.E001).exec()

	def clear_model(self):
		if self.project is not None:
			[self.view.scene().removeItem(i) for i in self.view.scene().items()]
		else:
			ErrorBox(**ErrorBox.E001).exec()

	def execute(self):
		if self.project is not None:
			if self.key is not None:
				self.executor = ModelExecutor(self.project, self.key)
				try:
					self.executor.beginExecution()
					self.modelUpdate.emit(self)
				except:
					ErrorBox(**ErrorBox.E005).exec()
					if DEBUG__: raise
			else:
				print("Error: Project File Interface key is empty")
		else:
			ErrorBox(**ErrorBox.E001).exec()


class ModelManager(QWidget):
	models: List[ModelWorkspace] = []

	modelUpdate = pyqtSignal("PyQt_PyObject")  # emits an update to any changes in the current model

	def __init__(self, proj: ProjectFI, parent=None):
		super().__init__(parent=parent)
		self.spacer = QVLine(visible=False)  # vertical spacer
		self.spacer.hide()
		self.cur_mdl: Optional[ModelWorkspace] = None
		self.project: Optional[ProjectFI] = proj

		self.inst_ui()
		self.add_model()

	def inst_ui(self):
		self.mdl_slctr = ModelWorkspaceSelector(self.models)
		self.mdl_slctr.activated.connect(lambda ind: self.select_model(ind))
		b_new_mdl = QPushButton("New Model")
		b_new_mdl.clicked.connect(lambda checked: self.add_model())
		b_rem_mdl = QPushButton("Remove Current Model")
		b_rem_mdl.clicked.connect(lambda checked: self.rem_model(self.cur_mdl))

		# b_rfr_mdl = QPushButton("Refresh")
		# b_rfr_mdl.clicked.connect(lambda checked: self.mdl_slctr.update_list(self.models))

		upper_menu = QHBoxLayout()
		upper_menu.addWidget(self.mdl_slctr)
		upper_menu.addWidget(b_new_mdl)
		upper_menu.addWidget(b_rem_mdl)
		upper_menu.addStretch()
		# upper_menu.addWidget(b_rfr_mdl)

		self.cur_mdl = None if len(self.models) == 0 else self.models[self.mdl_slctr.currentIndex()]

		self.central = QVBoxLayout()
		self.central.addLayout(upper_menu)
		self.central.addWidget(self.cur_mdl)
		self.central.addWidget(self.spacer)

		self.setLayout(self.central)

	def add_model(self):
		mdl_wksp = ModelWorkspace(self.project)
		mdl_wksp.nameChanged.connect(lambda s: self.mdl_slctr.update_list(self.models))
		mdl_wksp.modelUpdate.connect(lambda o: self.modelUpdate.emit(o))
		self.models.append(mdl_wksp)
		self.mdl_slctr.update_list(self.models)
		self.spacer.hide()

		self.select_model(self.mdl_slctr.count()-1)

	def select_model(self, ind: int):
		self.mdl_slctr.setCurrentIndex(ind)

		if self.cur_mdl is not None: self.cur_mdl.hide()
		self.cur_mdl = self.models[ind]
		self.cur_mdl.show()
		self.central.addWidget(self.cur_mdl)

	def rem_model(self, mdl_wrkspc: ModelWorkspace):
		if self.mdl_slctr.count() >= 2:
			self.models.remove(mdl_wrkspc)
			self.mdl_slctr.update_list(self.models)
			self.select_model(0)

			self.project.delete_mdl(mdl_wrkspc.key)
		elif self.mdl_slctr.count() == 1:
			self.models.remove(mdl_wrkspc)
			self.mdl_slctr.update_list(self.models)
			self.cur_mdl.hide()
			self.central.removeWidget(mdl_wrkspc)
			self.spacer.show()

			self.project.delete_mdl(mdl_wrkspc.key)
		else:
			print("Error: No more models!")

	def new_prj(self, proj: ProjectFI):  # the model workspace would be stayed as same
		print("PROJECT NEW")
		self.project = proj
		[mdl.update_proj(proj) for mdl in self.models]

	def load_prj(self, proj: ProjectFI):  # the loaded model workspace would APPEND the current workspace
		print("PROJECT LOAD")
		self.project = proj
		[mdl.update_proj(proj) for mdl in self.models]

		for mdl_key in self.project.project["model"]["tag"]:
			mdl_wksp = ModelWorkspace(self.project, inst_ui=False)
			mdl_wksp.key = mdl_key
			mdl_wksp.name = self.project.project["model"]["tag"][mdl_key]
			try:
				mdl_wksp.inst_ui(view=self.project.read_mdl_proj(mdl_key))
				self.models.append(mdl_wksp)
			except:
				ErrorBox(**ErrorBox.E006).exec()
				if DEBUG__: raise
		self.mdl_slctr.update_list(self.models)
