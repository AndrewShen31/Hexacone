from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QPoint, QMarginsF, QMargins
from PyQt5.QtWidgets import *

from typing import List, Tuple, Dict

from src.debug import *
from src.constants import *

from src.gfx.connector import Connector
from src.gfx.connection import Connection  # [WARN] diff between the import between src.gfx vs gfx


class Node(QGraphicsProxyWidget):
	""" Model Qt Graphical Wrapper Class
		This is to wrap the main model into a `QGraphicsProxyWidget` for serialization and customization processed
	"""
	def __init__(self, view, pos, nd_cls, parent=None):
		super().__init__(parent=parent)

		self.central = NodeInternal(view, pos, nd_cls, parent=None)
		self.setWidget(self.central)

	def __del__(self):
		# removes all the connector referring to this Node class
		[self.central.view.scene().removeItem(connc) for connc in self.central.connector]
		del self.central.connector[:]  # removes all Connector except the attribute itself


class NodeInternal(QWidget):
	""" Model Class
		This is to render a model, a configurable node for data manipulation and data transfer
	"""
	NODE_SIZE = (200, 50)
	CONNECTOR_SIZE = (16, 16)  # ~ connector size

	FIELD_PADY = 20  # field's padding on the y-axis
	FIELD_OFSY = 6  # field's offset on the y-axis
	MOUSE_OFS = (0, 0)  # position offset when mouse on trigger

	def __init__(self, view: QGraphicsView, pos: Tuple[int, int], nd_cls, parent=None):
		super().__init__(parent=parent)
		self.view = view

		self.clicked = False
		self.pos = pos
		self.nd_cls = nd_cls
		self.connector: List[Connector] = []

		self._inst_basic_ui(view)

		self.setStyleSheet("background-color: #CCDDFF")

	def _inst_basic_ui(self, view):  # graphics=Also instantiate/update graphical objects
		title = QLabel(self.nd_cls.name, self)
		title.setAlignment(Qt.AlignTop)
		title.setFont(QtGui.QFont("courier", 10, QtGui.QFont.Bold))
		title.setAlignment(Qt.AlignCenter)
		title.setStyleSheet("background-color: #CCF0FF")

		# === FIELD CREATION === #
		inp = QVBoxLayout()  # input area selection
		[inp.addWidget(QLabel(f[0])) for f in self.nd_cls.field["input"]]
		inp.addStretch()

		out = QVBoxLayout()  # output area selection
		[out.addWidget(QLabel(f[0])) for f in self.nd_cls.field["output"]]
		out.addStretch()

		usr = QFormLayout()  # user input area selection
		[usr.addRow(QLabel(f[0]), f[1]) for f in self.nd_cls.field["constant"]]

		# === LAYOUT CREATION === #
		data_selector = QBoxLayout(QBoxLayout.LeftToRight)  # a horizontal layout for input and output
		data_selector.addLayout(inp)
		data_selector.addStretch()
		data_selector.addLayout(out)

		top = QHBoxLayout()
		top.addWidget(title)
		# top.addWidget(QPushButton("[x]"))
		# top.setGeometry(QRect(0,0,100,100))


		layout = QVBoxLayout()
		layout.addLayout(top)
		layout.addLayout(data_selector)
		layout.addLayout(usr)
		layout.addStretch()

		self.setLayout(layout)
		self.setGeometry(self.pos[0], self.pos[1], self.NODE_SIZE[0], self.NODE_SIZE[1])

		# NOTE: The following initializes the starting position of the connector, which effects how the position of
		# the connector gets updated.
		for ind, fld in enumerate(self.nd_cls.field["input"]):
			o = Connector(QPoint(0, title.rect().height()+self.FIELD_PADY*ind+self.FIELD_OFSY),
						   TG_INPUT, [TG_OUTPUT], fld, view)
			self.connector.append(o)
			view.scene().addItem(o)
		for ind, fld in enumerate(self.nd_cls.field["output"]):
			o = Connector(QPoint(0, title.rect().height()+self.FIELD_PADY*ind+self.FIELD_OFSY),
						   TG_OUTPUT, [TG_INPUT], fld, view)
			self.connector.append(o)
			view.scene().addItem(o)
		self.updPosConnector()

	def resizeEvent(self, QResizeEvent):
		""" updates the position of all the connectors, espaically the output fields """
		for c in self.connector:
			if c.tag == "out":
				c.setX(self.NODE_SIZE[0]+QResizeEvent.size().width()-self.CONNECTOR_SIZE[0]/2)
			c.set_selector()
		self.updPosConnector()

	# built-in automatically called method
	def mousePressEvent(self, event):
		if event.button() == 1:  # 1 = left click
			self.clicked = True
			self.MOUSE_OFS = (-event.x(), -event.y())  # the event position is relative to this object

	# built-in automatically called method
	def mouseMoveEvent(self, event):
		if self.clicked:
			self.setGeometry(self.x()+event.x()+self.MOUSE_OFS[0], self.y()+event.y()+self.MOUSE_OFS[1],
			                 self.NODE_SIZE[0], self.NODE_SIZE[1])
			self.updPosConnector()

	# built-in automatically called method
	def mouseReleaseEvent(self, event):
		if event.button() == 1:  # 1 = left click
			self.clicked = False
			self.pos = (self.geometry().x(), self.geometry().y())

	# updates the position of the node
	def updPosConnector(self):
		new_pos = QPoint(self.geometry().x(), self.geometry().y())
		for c in self.connector:
			if c.tag == TG_INPUT:
				c.setPos(QPoint(new_pos.x()-self.CONNECTOR_SIZE[0]/2, new_pos.y()))
			elif c.tag == TG_OUTPUT:
				c.setPos(QPoint(new_pos.x()-self.CONNECTOR_SIZE[0]/2+self.width(), new_pos.y()))
			else:
				print("[MODEL] [ERROR] The node field is not in the model's field")

			# updates the position of the connector and the connector connecting to this connector
			for oline in self.view.items():
				if isinstance(oline, Connection):
					if oline.connector_b in self.connector:
						oline.update_pair()

			# updates the position of the `self.connector` of its conneciton
			for oline in c.connections:
				oline.update_pair()

		self.FIELD_OFSY = self.y()
