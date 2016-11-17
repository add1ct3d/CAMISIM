__author__ = 'hofmann'

import sys
import math
import textwrap
from scripts.Validator.validator import Validator


class MothurCluster(Validator):
	"""Reading and writing a meta table"""

	_label = "MothurCluster"

	def __init__(
		self, precision, otu_separator="\t", element_separator=",", iid_gid_mapping=None,
		logfile=None, verbose=False, debug=False):
		"""
		Constructor

		@param precision: Cluster are made in steps: 10: 0.1, 100: 0.01, 1000: 0.001
		@type precision: int | long
		@param otu_separator: Character separating otu cluster from another
		@type otu_separator: str | unicode
		@param element_separator: Character separating elements within otu cluster from another
		@type element_separator: str | unicode
		@param iid_gid_mapping: Map of internal ids to genome ids
		@type iid_gid_mapping: dict[str|unicode, str|unicode]
		@param logfile: File handler or file path to a log file
		@type logfile: file | FileIO | StringIO | basestring
		@param verbose: Not verbose means that only warnings and errors will be past to stream
		@type verbose: bool
		@param debug: Display debug messages
		@type debug: bool
		"""
		assert isinstance(precision, int)
		assert self.validate_number(precision, minimum=0)
		assert isinstance(otu_separator, basestring)
		assert isinstance(element_separator, basestring)
		assert iid_gid_mapping is None or isinstance(iid_gid_mapping, dict)
		super(MothurCluster, self).__init__(logfile=logfile, verbose=verbose, debug=debug)
		self._precision = int(math.log10(precision))
		self._cluster_separator = otu_separator
		self._element_separator = element_separator
		self._cutoff_to_cluster = {}
		self._gid_to_cluster_index_list = {}
		self._unique_threshold = "unique"
		self._iid_gid = {}
		if iid_gid_mapping is not None:
			self._iid_gid = iid_gid_mapping

	def iid_to_gid_list(self, list_iid):
		"""
		Change a iid list to a genome id list

		@param list_iid: List of iid, like from a cluster
		@type list_iid: list[str|unicode]

		@return: List of gid
		@rtype: list[str|unicode]
		"""
		assert isinstance(list_iid, list)
		list_gid = []
		for iid in list_iid:
			list_gid.append(self._iid_gid[iid])
		return list_gid

	def has_threshold(self, threshold):
		"""
		True if a threshold is available.

		@param threshold: Specific cluster threshold
		@type threshold: str|unicode | int|float

		@return: list of cluster index and a list of those clusters
		@rtype: bool
		"""
		assert isinstance(threshold, (int, float, basestring))
		return threshold in self._cutoff_to_cluster

	def get_max_threshold(self):
		"""
		Get highest threshold

		@return: Highest threshold
		@rtype: str | unicode
		"""
		lists_of_thresholds = list(self._cutoff_to_cluster.keys())
		lists_of_thresholds.remove(self._unique_threshold)
		lists_of_thresholds = sorted(lists_of_thresholds)
		if len(lists_of_thresholds) == 0:
			return self._unique_threshold
		return lists_of_thresholds[-1]

	def read(self, file_path, list_of_query_id=None):
		"""
		Read a otu cluster file generated by mothur

		@param file_path: File path to otu cluster file generated by mothur
		@type file_path: str | unicode
		@param list_of_query_id: removes elements of query from clusters and remembers the index of cluster those were in
		@type list_of_query_id: list[str|unicode]

		@type: None
		"""
		assert self.validate_file(file_path)
		assert list_of_query_id is None or isinstance(list_of_query_id, (list, set))
		self._logger.info("Reading cluster file '{}'".format(file_path))

		with open(file_path) as file_handler:
			self._gid_to_cluster_index_list = {}
			for line in file_handler:
				line = line.strip()
				if line.startswith('#') or line.startswith("label") or len(line) == 0:
					continue
				list_of_cluster = []
				row = line.split(self._cluster_separator)
				cutoff = row[0]
				if cutoff.isdigit():
					cutoff = str(float(cutoff))
				cluster_amount = row[1]
				self._logger.debug("Reading threshold: {}".format(cutoff))
				self._gid_to_cluster_index_list[cutoff] = {}
				cluster_index = 0
				for cluster_as_string in row[2:]:
					set_of_elements = set(cluster_as_string.split(self._element_separator))
					remove_list = set()
					if list_of_query_id:
						for iid in set_of_elements:
							gid = self._iid_gid[iid]
							if gid not in list_of_query_id:
								continue
							remove_list.add(iid)
							if gid not in self._gid_to_cluster_index_list[cutoff]:
								self._gid_to_cluster_index_list[cutoff][gid] = []
							self._gid_to_cluster_index_list[cutoff][gid].append(cluster_index)
						cluster_index += 1
					list_of_cluster.append(list(set_of_elements.difference(remove_list)))
				self._cutoff_to_cluster[cutoff] = {"count": cluster_amount, "cluster": list_of_cluster}

	def get_prediction_thresholds(self, minimum=0):
		"""
		Get a set of thresholds above a given minimum

		@param minimum: Minimum threshold
		@type minimum: int | float

		@return: Set of thresholds above a given minimum
		@rtype: set[str|unicode]
		"""
		assert self.validate_number(minimum, minimum=0, maximum=1)
		subset = set()
		list_of_cutoff = list(self._cutoff_to_cluster.keys())
		list_as_float = []
		for cutoff in list_of_cutoff:
			if '.' not in cutoff:
				continue
			list_as_float.append(float(cutoff))

		for cutoff in list_of_cutoff:
			if '.' not in cutoff:
				continue
			threshold = round(float(cutoff), self._precision)

			if threshold >= minimum and threshold in list_as_float:
				subset.add(threshold)
		return subset

	def get_sorted_lists_of_thresholds(self, reverse=False):
		"""
		Get sorted list of thresholds

		@param reverse: True for a reversed list
		@type reverse: bool

		@return: List of thresholds
		@rtype: list[str|unicode]
		"""
		assert isinstance(reverse, bool)
		lists_of_cutoff = list(self._cutoff_to_cluster.keys())
		lists_of_cutoff.remove("unique")
		lists_of_cutoff = sorted(lists_of_cutoff, reverse=reverse)
		if not reverse:
			tmp = lists_of_cutoff
			lists_of_cutoff = ["unique"]
			lists_of_cutoff.extend(tmp)
		else:
			lists_of_cutoff.append("unique")
		return lists_of_cutoff

	def cluster_list_to_stream(self, list_of_cluster, stream=sys.stdout, width=80):
		"""
		Stream a cluster

		@param list_of_cluster: List of internal ids
		@type list_of_cluster: list[str|unicode] | dict[str|unicode, str|unicode]
		@param stream: File handle or something
		@type stream: file | FileIO | StringIO
		@param width: Wrap output to a width
		@type width: int

		@rtype: None
		"""
		assert self.is_stream(stream)
		assert isinstance(list_of_cluster, (dict, list))
		if not isinstance(list_of_cluster, dict):
			stream.write(textwrap.fill(", ".join(list_of_cluster) + '\n', width))
		else:
			line = ", ".join('{}: {}'.format(key, value) for key, value in list_of_cluster.items())
			stream.write(textwrap.fill(line, width) + '\n')

	def element_exists(self, threshold, gid):
		"""
		Test if a genome id is available

		@param threshold: Specific cluster threshold to look in
		@type threshold: str|unicode | int|float
		@param gid: genome id to look for
		@type gid: str|unicode

		@return: True if genome id available in data
		@rtype: bool
		"""
		assert isinstance(threshold, (int, float, basestring))
		assert isinstance(gid, basestring)
		if not threshold == "unique":
			assert isinstance(threshold, (int, float))
			threshold = "{th:.{pre}f}".format(th=threshold, pre=self._precision)

		if threshold not in self._gid_to_cluster_index_list:
			self._logger.error("Cutoff key error: {}\nAvailable keys: '{}'".format(threshold, ','.join(self._gid_to_cluster_index_list.keys())))
			return False

		if gid not in self._gid_to_cluster_index_list[threshold]:
			# 	self.logger.warning("{} not found in {}".format(element, cutoff))
			return False
		return True

	def get_cluster_of_threshold_of_index(self, threshold, cluster_index):
		"""
		Get the list of internal ids of a otu cluster

		@param threshold: Specific cluster threshold to look in
		@type threshold: str|unicode | int|float
		@param cluster_index: Index of a cluster
		@type cluster_index: int | long

		@return: List of internal ids of a otu cluster
		@rtype: list[str|unicode]
		"""
		assert isinstance(threshold, (int, float, basestring))
		assert isinstance(cluster_index, (int, float))
		if threshold not in self._cutoff_to_cluster:
			self._logger.error("Bad cutoff {}".format(threshold))
			return None
		if cluster_index >= len(self._cutoff_to_cluster[threshold]["cluster"]):
			self._logger.error("Bad cluster index".format(cluster_index))
			return None
		return self._cutoff_to_cluster[threshold]["cluster"][cluster_index]

	def get_cluster_of_threshold_of_gid(self, threshold, gid):
		"""
		Get list of cluster of a genome id at a threshold

		@param threshold: Specific cluster threshold
		@type threshold: str|unicode | int|float
		@param gid: genome id to look for
		@type gid: str|unicode

		@return: list of cluster index and a list of those clusters
		@rtype: tuple[int|long, list[list[str|unicode]]]
		"""
		assert isinstance(threshold, (int, float, basestring))
		assert isinstance(gid, basestring)
		if not threshold == "unique":
			assert isinstance(threshold, (int, float))
			threshold = "{th:.{pre}f}".format(th=threshold, pre=self._precision)

		if threshold not in self._cutoff_to_cluster:
			self._logger.error("Bad cutoff: {}".format(threshold))
			return [], []
		if not self.element_exists(float(threshold), gid) or gid.strip() == '' or threshold.strip() == '':
			self._logger.warning("Bad element: {} in {}".format(gid, threshold))
			return [], []
		list_of_index = self._gid_to_cluster_index_list[threshold][gid]
		if len(set(list_of_index)) > 1:
			self._logger.debug("{}: Multiple elements found. {}: {}".format(threshold, gid, ", ".join([str(item) for item in set(list_of_index)])))
		return list_of_index, [self._cutoff_to_cluster[threshold]["cluster"][index] for index in list_of_index]

	def get_cluster_of_cutoff(self, threshold="unique"):
		"""
		Get all cluster of a threshold

		@param threshold: Cluster threshold
		@type threshold: str|unicode | int|float

		@return: List of cluster
		@rtype: list[list[str|unicode]]]
		"""
		assert isinstance(threshold, (int, float, basestring))
		if not threshold == "unique":
			assert isinstance(threshold, (int, float))
			threshold = "{th:.{pre}f}".format(th=threshold, pre=self._precision)

		if threshold not in self._cutoff_to_cluster:
			if self._logger:
				self._logger.error("Bad cutoff: {}".format(threshold))
			return None
		return self._cutoff_to_cluster[threshold]["cluster"]

	def get_cluster_count_of_cutoff(self, threshold="unique"):
		"""
		Get amount of cluster at a threshold

		@param threshold: Cluster threshold
		@type threshold: str|unicode | int|float

		@return: Amount of cluster
		@rtype: int | long
		"""
		assert isinstance(threshold, (int, float, basestring))
		if not threshold == "unique":
			assert isinstance(threshold, (int, float))
			threshold = "{th:.{pre}f}".format(th=threshold, pre=self._precision)

		if threshold not in self._cutoff_to_cluster:
			if self._logger:
				self._logger.error("Bad cutoff: {}".format(threshold))
			return None
		return self._cutoff_to_cluster[threshold]["count"]

	def cluster_at_threshold_to_string(self, threshold="unique"):
		"""
		Return the cluster at a threshold as string

		@param threshold: Cluster threshold
		@type threshold: str|unicode | int|float

		@return: Cluster at a threshold as string
		@rtype: str|unicode
		"""
		assert isinstance(threshold, (int, float, basestring))
		if not threshold == "unique":
			assert isinstance(threshold, (int, float))
			threshold = "{th:.{pre}f}".format(th=threshold, pre=self._precision)

		result_string = "{}\n".format(threshold)
		if threshold not in self._cutoff_to_cluster:
			if self._logger:
				self._logger.error("Bad cutoff: {}".format(threshold))
			return None
		for otu_group in self._cutoff_to_cluster[threshold]["cluster"]:
			result_string += ", ".join(otu_group) + '\n'
		return result_string
