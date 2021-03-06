from src.debug import print
from src.interface.project_file_interface import ProjectFI
from src.constants import Null
from src.components.workspace.connector_type import ConnectorType as CT

import ast

import pandas as pd
import numpy as np

from typing import List


class ModelExecutor:
	# indexes
	FLD_TYP = 0
	IO_TYP = 1
	IO_CONNECT = 2
	IO_VAL = 3
	CONST_VAL = 1

	# t := type
	tINP = "INP"
	tOUT = "OUT"
	tCONST = "CNST"


	def __init__(self, proj: ProjectFI, key: int):
		self.tree, self.id_map = proj.read_mdl_exec(key)
		self.completed: List[dict] = []  # a list of index reference to the model in the tree that are FINISHED executing

		from src.components.workspace import nodes

		mdl_cls_ref = [nodes.__dict__[c] for c in nodes.__dir__()
		           if type(nodes.__dict__[c]) == type
		           if nodes.__dict__[c].__module__ == nodes.__name__
		           ]

		self.mdl_map = {o.title: o for o in mdl_cls_ref}

		self.instance = {
			"root": proj.path,
		}

	def beginExecution(self):
		self.execAnchor()  # executes all the anchor to set-up the main execution
		self.execMain()  # executes all the remaining nodes

	def execMain(self):

		buf0 = []
		buf1 = []
		while True:
			if self.completed == buf1 == buf0:  # once all of the node has been executed except the malfunctioned nodes will end the executor
				break
			buf0 = buf1.copy()
			buf1 = self.completed.copy()

			for node in self.tree:
				if node not in self.completed:
					success = self.execNode(node)
					if success: self.completed.append(node)

			if set(self.tree.keys()) == set(self.completed):  # once all of the tree is completed
				break

	def execAnchor(self):
		anchor = []  # models that should start the execution; it is a list of the reference

		for node in self.tree:
			hasInput = False
			for field in self.tree[node]:
				if self.tree[node][field][self.FLD_TYP] == self.tINP:
					hasInput = True
					break

			if not hasInput: anchor.append(node)

		for node in anchor:
			success = self.execNode(node)
			if success: self.completed.append(node)


	def execNode(self, node: int):
		model_class = self.mdl_map[self.id_map[node]]
		model_incomplete = False
		model_type_error = []  # []: No Error; [{field name (INP): field type, field name(OUT): field type},...]

		inp_field = {}
		for field in self.tree[node]:
			int_fdata = self.tree[node][field]  # internal field data; improve readability
			if int_fdata[self.FLD_TYP] == self.tINP:
				if self._is_null(int_fdata[self.IO_VAL]):
					if int_fdata[self.IO_CONNECT] == []:  # When the input value itself is None and HAS NO connection
						ext_val = []
						# to find value when there are no connections and the value is none
						for ext_node in self.tree:
							for ext_field in self.tree[ext_node]:
								ext_fdata = self.tree[ext_node][ext_field]  # external field data; improve readability
								if ext_fdata[self.FLD_TYP] == self.tOUT:
									# note: the pandas dataframe results a value error because of ambiguity and trying to cast the dataframe so it can easily be compared
									if field in ext_fdata[self.IO_CONNECT] and not self._is_null(ext_fdata[self.IO_VAL]):
										if self._compat_type(int_fdata[self.IO_TYP], ext_fdata[self.IO_TYP]):
											ext_val.append(ext_fdata[self.IO_VAL])
										else: model_incomplete = True; model_type_error.append({self.id_map[field]: int_fdata[self.IO_TYP], self.id_map[ext_field]: ext_fdata[self.IO_TYP]})
						if ext_val != []:
							inp_field[self.id_map[field]] = ext_val[-1]  # edit this for different summation from multiple values
						else: model_incomplete = True; break
					else:  # When the input value itself is None and HAS connection
						ext_val = []
						# to find value when there are no connections and the value is none
						for ext_node in self.tree:
							for ext_field in self.tree[ext_node]:
								ext_fdata = self.tree[ext_node][ext_field]  # external field data; improve readability
								if ext_fdata[self.FLD_TYP] == self.tOUT:
									if ext_field in int_fdata[self.IO_CONNECT] and not self._is_null(ext_fdata[self.IO_VAL]):
										if self._compat_type(int_fdata[self.IO_TYP], ext_fdata[self.IO_TYP]):
											ext_val.append(ext_fdata[self.IO_VAL])
										else: model_incomplete = True; model_type_error.append({self.id_map[field]: int_fdata[self.IO_TYP], self.id_map[ext_field]: ext_fdata[self.IO_TYP]})
						if ext_val != []:
							inp_field[self.id_map[field]] = ext_val[-1]  # edit this for different summation from multiple values
						else: model_incomplete = True; break
				else:  # When the input value itself has already have a value
					inp_field[self.id_map[field]] = self.tree[node][field][self.IO_VAL]

		const_field = {}
		for field in self.tree[node]:
			if self.tree[node][field][self.FLD_TYP] == self.tCONST:
				if not self._is_null(self.tree[node][field][self.CONST_VAL]):
					const_field[self.id_map[field]] = self.tree[node][field][self.CONST_VAL]
				else: model_incomplete = True; break

		out_field = {}
		for field in self.tree[node]:
			if self.tree[node][field][self.FLD_TYP] == self.tOUT:
				out_field[self.id_map[field]] = Null

		if not model_incomplete:
			fnlMod = lambda dct: {k:self._type_conversion(dct[k]) for k in dct}

			out_data = model_class.execute(inp=fnlMod(inp_field), const=fnlMod(const_field), out=fnlMod(out_field), inst=fnlMod(self.instance))

			if [fld for fld in out_data if fld == Null] == []:  # shows all the output data has been set (not Null)
				for field in self.tree[node]:  # sets all the output data to the main tree
					if self.tree[node][field][self.FLD_TYP] == self.tOUT:
						self.tree[node][field][self.IO_VAL] = out_data[self.id_map[field]]
				return True
			else:
				print(f"WARNING: The model <{self.id_map[node]}> has not completed all of its output")
				return False
		else:
			return False

	def _type_conversion(self, string):
		try: return ast.literal_eval(string)
		except Exception: return string

	def _is_null(self, val):  # check if the input value is null
		if type(val) in [pd.Series, pd.DataFrame, np.ndarray]:  # if you know the type, it means its not Null
			return False
		return val == Null

	def _compat_type(self, typ1, typ2):
		# TODO: Make the Any type mechanism compatible to *any* type
		# TODO: Make the Int compatible to both Int and Bool
		# note: Scalar | Any is incompat to Matrix | Any
		typ1 = int(typ1) if type(typ1) == str else typ1
		typ2 = int(typ2) if type(typ2) == str else typ2

		if typ1 == typ2:
			return True
		else:
			return False
