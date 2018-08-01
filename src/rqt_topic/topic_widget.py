#!/usr/bin/env python

# Copyright (c) 2011, Dorian Scholz, TU Darmstadt
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met: 
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#   * Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#   * Neither the name of the TU Darmstadt nor the names of its
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import division
import os

from python_qt_binding import loadUi
from python_qt_binding.QtCore import Qt, QTimer, Signal, Slot
from python_qt_binding.QtGui import QIcon
from python_qt_binding.QtWidgets import QHeaderView, QMenu, QTreeWidgetItem, QWidget, QFileDialog
import roslib
import rospkg
import rospy
from rospy.exceptions import ROSException
from .topic_info import TopicInfo




class TopicWidget(QWidget):
    """
    main class inherits from the ui window class.

    You can specify the topics that the topic pane.

    TopicWidget.start must be called in order to update topic pane.
    """

    SELECT_BY_NAME = 0
    SELECT_BY_MSGTYPE = 1

    _column_names = ['topic', 'type', 'bandwidth', 'rate', 'value']

    def __init__(self, plugin=None, selected_topics=None, select_topic_type=SELECT_BY_NAME):
        """
        @type selected_topics: list of tuples.
        @param selected_topics: [($NAME_TOPIC$, $TYPE_TOPIC$), ...]
        @type select_topic_type: int
        @param select_topic_type: Can specify either the name of topics or by
                                  the type of topic, to filter the topics to
                                  show. If 'select_topic_type' argument is
                                  None, this arg shouldn't be meaningful.
        """
        super(TopicWidget, self).__init__()

        self._select_topic_type = select_topic_type

        rp = rospkg.RosPack()
        ui_file = os.path.join(rp.get_path('rqt_topic'), 'resource', 'TopicWidget.ui')
        loadUi(ui_file, self)
        self._plugin = plugin
        self.topics_tree_widget.sortByColumn(0, Qt.AscendingOrder)
        header = self.topics_tree_widget.header()
        try:
            setSectionResizeMode = header.setSectionResizeMode  # Qt5
        except AttributeError:
            setSectionResizeMode = header.setResizeMode  # Qt4
        setSectionResizeMode(QHeaderView.ResizeToContents)
        header.customContextMenuRequested.connect(self.handle_header_view_customContextMenuRequested)
        header.setContextMenuPolicy(Qt.CustomContextMenu)

        # Whether to get all topics or only the topics that are set in advance.
        # Can be also set by the setter method "set_selected_topics".
        self._selected_topics = selected_topics
        self._current_topic_list = []
        self._topics = {}
        self._tree_items = {}
        self._column_index = {}
        for column_name in self._column_names:
            self._column_index[column_name] = len(self._column_index)

        # self.refresh_topics()

        # init and start update timer
        self._timer_refresh_topics = QTimer(self)
        self._timer_refresh_topics.timeout.connect(self.refresh_topics)

	# Mon code
	self._generation_code_class = Genecode(self) #_valider_#
	self._pub_sub = Pub_Sub(self._generation_code_class) #_valider_#
	self._node_generation_main = Node_generation_main(self._pub_sub)
 	self._interface_pub_sub = Interface_Pub_Sub(self,self._generation_code_class,self._pub_sub,self._node_generation_main) #_valider_#
	self.code_generation_button.clicked.connect(self._interface_pub_sub._press_button_code) #_valider_#


    def set_topic_specifier(self, specifier):
        self._select_topic_type = specifier


    def start(self):
        """
        This method needs to be called to start updating topic pane.
        """
        self._timer_refresh_topics.start(1000)

    @Slot()
    def refresh_topics(self):
        """
        refresh tree view items
        """
        try:
            if self._selected_topics is None:
                topic_list = rospy.get_published_topics()
                if topic_list is None:
                    rospy.logerr('Not even a single published topic found. Check network configuration')
                    return
            else:  # Topics to show are specified.
                topic_list = self._selected_topics
                topic_specifiers_server_all = None
                topic_specifiers_required = None

                rospy.logdebug('refresh_topics) self._selected_topics=%s' % (topic_list,))

                if self._select_topic_type == self.SELECT_BY_NAME:
                    topic_specifiers_server_all = [name for name, type in rospy.get_published_topics()]
                    topic_specifiers_required = [name for name, type in topic_list]
                elif self._select_topic_type == self.SELECT_BY_MSGTYPE:
                    # The topics that are required (by whoever uses this class).
                    topic_specifiers_required = [type for name, type in topic_list]

                    # The required topics that match with published topics.
                    topics_match = [(name, type) for name, type in rospy.get_published_topics() if type in topic_specifiers_required]
                    topic_list = topics_match
                    rospy.logdebug('selected & published topic types=%s' % (topic_list,))

                rospy.logdebug('server_all=%s\nrequired=%s\ntlist=%s' % (topic_specifiers_server_all, topic_specifiers_required, topic_list))
                if len(topic_list) == 0:
                    rospy.logerr('None of the following required topics are found.\n(NAME, TYPE): %s' % (self._selected_topics,))
                    return
        except IOError as e:
            rospy.logerr("Communication with rosmaster failed: {0}".format(e.strerror))
            return

        if self._current_topic_list != topic_list:
            self._current_topic_list = topic_list

            # start new topic dict
            new_topics = {}

            for topic_name, topic_type in topic_list:
                # if topic is new or has changed its type
                if topic_name not in self._topics or \
                   self._topics[topic_name]['type'] != topic_type:
                    # create new TopicInfo
                    topic_info = TopicInfo(topic_name, topic_type)
                    message_instance = None
                    if topic_info.message_class is not None:
                        message_instance = topic_info.message_class()
                    # add it to the dict and tree view
		    self._topic_type = topic_type
                    topic_item = self._recursive_create_widget_items(self.topics_tree_widget, topic_name, topic_type, message_instance)
                    new_topics[topic_name] = {
                       'item': topic_item,
                       'info': topic_info,
                       'type': topic_type,
                    }
                else:
                    # if topic has been seen before, copy it to new dict and
                    # remove it from the old one
                    new_topics[topic_name] = self._topics[topic_name]
                    del self._topics[topic_name]

            # clean up old topics
            for topic_name in self._topics.keys():
                self._topics[topic_name]['info'].stop_monitoring()
                index = self.topics_tree_widget.indexOfTopLevelItem(
                                           self._topics[topic_name]['item'])
                self.topics_tree_widget.takeTopLevelItem(index)
                del self._topics[topic_name]

            # switch to new topic dict
            self._topics = new_topics
        self._update_topics_data()

    def _update_topics_data(self):
        for topic in self._topics.values():
            topic_info = topic['info']
            if topic_info.monitoring:
                # update rate
                rate, _, _, _ = topic_info.get_hz()
                rate_text = '%1.2f' % rate if rate != None else 'unknown'

                # update bandwidth
                bytes_per_s, _, _, _ = topic_info.get_bw()
                if bytes_per_s is None:
                    bandwidth_text = 'unknown'
                elif bytes_per_s < 1000:
                    bandwidth_text = '%.2fB/s' % bytes_per_s
                elif bytes_per_s < 1000000:
                    bandwidth_text = '%.2fKB/s' % (bytes_per_s / 1000.)
                else:
                    bandwidth_text = '%.2fMB/s' % (bytes_per_s / 1000000.)

                # update values
                value_text = ''
                self.update_value(topic_info._topic_name, topic_info.last_message)

            else:
                rate_text = ''
                bytes_per_s = None
                bandwidth_text = ''
                value_text = 'not monitored' if topic_info.error is None else topic_info.error

            self._tree_items[topic_info._topic_name].setText(self._column_index['rate'], rate_text)
            self._tree_items[topic_info._topic_name].setData(self._column_index['bandwidth'], Qt.UserRole, bytes_per_s)
            self._tree_items[topic_info._topic_name].setText(self._column_index['bandwidth'], bandwidth_text)
            self._tree_items[topic_info._topic_name].setText(self._column_index['value'], value_text)

    def update_value(self, topic_name, message):
        if hasattr(message, '__slots__') and hasattr(message, '_slot_types'):
            for slot_name in message.__slots__:
                self.update_value(topic_name + '/' + slot_name, getattr(message, slot_name))

        elif type(message) in (list, tuple) and (len(message) > 0) and hasattr(message[0], '__slots__'):

            for index, slot in enumerate(message):
                if topic_name + '[%d]' % index in self._tree_items:
                    self.update_value(topic_name + '[%d]' % index, slot)
                else:
                    base_type_str, _ = self._extract_array_info(self._tree_items[topic_name].text(self._column_index['type']))
                    self._recursive_create_widget_items(self._tree_items[topic_name], topic_name + '[%d]' % index, base_type_str, slot)
            # remove obsolete children
            if len(message) < self._tree_items[topic_name].childCount():
                for i in range(len(message), self._tree_items[topic_name].childCount()):
                    item_topic_name = topic_name + '[%d]' % i
                    self._recursive_delete_widget_items(self._tree_items[item_topic_name])
        else:
            if topic_name in self._tree_items:
                self._tree_items[topic_name].setText(self._column_index['value'], repr(message))

    def _extract_array_info(self, type_str):
        array_size = None
        if '[' in type_str and type_str[-1] == ']':
            type_str, array_size_str = type_str.split('[', 1)
            array_size_str = array_size_str[:-1]
            if len(array_size_str) > 0:
                array_size = int(array_size_str)
            else:
                array_size = 0
        return type_str, array_size

    def _recursive_create_widget_items(self, parent, topic_name, type_name, message):
        if parent is self.topics_tree_widget:
            # show full topic name with preceding namespace on toplevel item
            topic_text = topic_name
            item = TreeWidgetItem(self._toggle_monitoring, topic_name, parent)
        else:
            topic_text = topic_name.split('/')[-1]
            if '[' in topic_text:
                topic_text = topic_text[topic_text.index('['):]
            item = QTreeWidgetItem(parent)
        item.setText(self._column_index['topic'], topic_text)
        item.setText(self._column_index['type'], type_name)
        item.setData(0, Qt.UserRole, topic_name)


        self._tree_items[topic_name] = item
        if hasattr(message, '__slots__') and hasattr(message, '_slot_types'):
            for slot_name, type_name in zip(message.__slots__, message._slot_types):
                self._recursive_create_widget_items(item, topic_name + '/' + slot_name, type_name, getattr(message, slot_name))

        else:
            base_type_str, array_size = self._extract_array_info(type_name)
            try:
                base_instance = roslib.message.get_message_class(base_type_str)()
            except (ValueError, TypeError):
                base_instance = None
            if array_size is not None and hasattr(base_instance, '__slots__'):
                for index in range(array_size):
                    self._recursive_create_widget_items(item, topic_name + '[%d]' % index, base_type_str, base_instance)

        return item


    def _toggle_monitoring(self, topic_name):
        item = self._tree_items[topic_name]
        if item.checkState(0):
            self._topics[topic_name]['info'].start_monitoring()
	    self._generation_code_class._add_topic_name_and_type_to_variables(topic_name)#_valider_#
	    if item.checkState(5):
		self._generation_code_class._add_subscriber_to_variable(topic_name)
	    else: 
		self._generation_code_class._remove_subscriber_to_variable(topic_name)
	    if item.checkState(6):
		self._generation_code_class._add_publisher_to_variable(topic_name)
	    else: 
		self._generation_code_class._remove_publisher_to_variable(topic_name)
	else: 
            self._topics[topic_name]['info'].stop_monitoring()
	    self._generation_code_class._remove_topic_name_and_type_to_variables(topic_name) 
	    self._generation_code_class._remove_subscriber_to_variable(topic_name)
	    self._generation_code_class._remove_publisher_to_variable(topic_name)

    def _recursive_delete_widget_items(self, item):
        def _recursive_remove_items_from_tree(item):
            for index in reversed(range(item.childCount())):
                _recursive_remove_items_from_tree(item.child(index))
            topic_name = item.data(0, Qt.UserRole)
            del self._tree_items[topic_name]
        _recursive_remove_items_from_tree(item)
        item.parent().removeChild(item)
        


    @Slot('QPoint')
    def handle_header_view_customContextMenuRequested(self, pos):
        header = self.topics_tree_widget.header()

        # show context menu
        menu = QMenu(self)
        action_toggle_auto_resize = menu.addAction('Toggle Auto-Resize')
        action = menu.exec_(header.mapToGlobal(pos))

        # evaluate user action
        if action is action_toggle_auto_resize:
            try:
                sectionResizeMode = header.sectionResizeMode  # Qt5
                setSectionResizeMode = header.setSectionResizeMode  # Qt5
            except AttributeError:
                sectionResizeMode = header.resizeMode  # Qt4
                setSectionResizeMode = header.setResizeMode  # Qt4
            if sectionResizeMode(0) == QHeaderView.ResizeToContents:
                setSectionResizeMode(QHeaderView.Interactive)
            else:
                setSectionResizeMode(QHeaderView.ResizeToContents)

    @Slot('QPoint')
    def on_topics_tree_widget_customContextMenuRequested(self, pos):
        item = self.topics_tree_widget.itemAt(pos)
        if item is None:
            return

        # show context menu
        menu = QMenu(self)
        action_item_expand = menu.addAction(QIcon.fromTheme('zoom-in'), 'Expand All Children')
        action_item_collapse = menu.addAction(QIcon.fromTheme('zoom-out'), 'Collapse All Children')
        action = menu.exec_(self.topics_tree_widget.mapToGlobal(pos))

        # evaluate user action
        if action in (action_item_expand, action_item_collapse):
            expanded = (action is action_item_expand)

            def recursive_set_expanded(item):
                item.setExpanded(expanded)
                for index in range(item.childCount()):
                    recursive_set_expanded(item.child(index))
            recursive_set_expanded(item)

    def shutdown_plugin(self):
        for topic in self._topics.values():
            topic['info'].stop_monitoring()
        self._timer_refresh_topics.stop()

    def set_selected_topics(self, selected_topics):
        """
        @param selected_topics: list of tuple. [(topic_name, topic_type)]
        @type selected_topics: []
        """
        rospy.logdebug('set_selected_topics topics={}'.format(
                                                         len(selected_topics)))
        self._selected_topics = selected_topics
	

    # TODO(Enhancement) Save/Restore tree expansion state
    def save_settings(self, plugin_settings, instance_settings):
        header_state = self.topics_tree_widget.header().saveState()
        instance_settings.set_value('tree_widget_header_state', header_state)

    def restore_settings(self, pluggin_settings, instance_settings):
        if instance_settings.contains('tree_widget_header_state'):
            header_state = instance_settings.value('tree_widget_header_state')
            if not self.topics_tree_widget.header().restoreState(header_state):
                rospy.logwarn("rqt_topic: Failed to restore header state.")

class TreeWidgetItem(QTreeWidgetItem):
    def __init__(self, check_state_changed_callback, topic_name, parent=None):
        super(TreeWidgetItem, self).__init__(parent)
        self._check_state_changed_callback = check_state_changed_callback
        self._topic_name = topic_name
        self.setCheckState(0, Qt.Unchecked)
	self.setCheckState(5, Qt.Unchecked)
	self.setCheckState(6, Qt.Unchecked)


    def setData(self, column, role, value):
        if role == Qt.CheckStateRole:
            state = self.checkState(column)
        super(TreeWidgetItem, self).setData(column, role, value)
        if role == Qt.CheckStateRole and state != self.checkState(column):
            self._check_state_changed_callback(self._topic_name)

    def __lt__(self, other_item):
        column = self.treeWidget().sortColumn()
        if column == TopicWidget._column_names.index('bandwidth'):
            return self.data(column, Qt.UserRole) < other_item.data(column, Qt.UserRole)
        return super(TreeWidgetItem, self).__lt__(other_item)


class Interface_Pub_Sub():#_Valider_#-----------------------------
	def __init__(self,topicwidget,Genecode,Pub_Sub,Node_generation_main):
        	#super(Interface_Pub_Sub, self).__init__()
		self._genecode = Genecode
		self._pub_sub = Pub_Sub
		self._topicwidget=topicwidget
		self._node_generation_main = Node_generation_main
		self._frequency_code = 0
		self._topicwidget.frequency_box.setMaximum(10000)
		self._name_of_file()
	
	def _press_button_directory(self):
		filename = QFileDialog.getSaveFileName(self, 'Save to File', '.', self.tr('rqt_console msg file {.csv} (*.csv)'))
		print(filename)
		
		
		
	def _press_button_code(self):
		if (not(self._genecode._list_topics_name_selected) ) :
			print "Generation impossible: empty list"
		else :

			self._name_of_file() #Recupere le nom choisie pour le fichier
			self._get_frequency()
			self._pub_sub._generation_code_class_command()
			self._node_generation_main._generation_code_main()
			print "Code generation finish"
	
	def _name_of_file(self):
		self._name_file = self._topicwidget.name_line_edit.text()

	def _get_frequency(self):
		if (self._topicwidget.frequency_box.value() == 0 ) :
			self._frequency_code = 10
		else :
			self._frequency_code = self._topicwidget.frequency_box.value()
		return self._frequency_code

class Genecode():#_valider_#-----------------------------
	"""
	This class generates two files containing the names and types of the selected topics. 
	Those two files are generated in the current working directory. 
	This class handles the call towards the generation of publishers and subscribers
	"""
    	def __init__(self,topicwidget):
		self._list_topics_name_selected = [] #Liste pour stocker le nom des topics selectionnes		
		self._list_topics_name_sub_selected = []
		self._list_topics_name_pub_selected = []
		self._dict_topics = {}


		self._topicwidget=topicwidget


    	def _write_topic_into_file(self):#Ma fonction pour ecrire dans un fichier
		my_file = open("dict_topics_name_selected.txt","w")#Destination du fichier
		my_file.write('{0}'.format(self._dict_topics))#Ecriture dans le fichier
		my_file.close()#Fermeture du fichier

	
	def _add_topic_name_and_type_to_variables(self, topic_name):
	    	self._list_topics_name_selected.append(topic_name)#Ajoute le nom du topic dans la liste 
		self._list_topics_name_selected = list(set(self._list_topics_name_selected))
		self._topic_item_type = self._topicwidget._topics[topic_name]
		self._dict_topics[topic_name]= self._topic_item_type["type"]




	def _remove_topic_name_and_type_to_variables(self, topic_name):
		if (  (len(topic_name) != 0 ) and (len(self._list_topics_name_selected)!=0 ) and (topic_name in self._list_topics_name_selected) ):
		    	self._list_topics_name_selected.remove(topic_name)#Supprime le nom du topic dans la liste 
			del self._dict_topics[topic_name]



	def _add_subscriber_to_variable(self,topic_name):
		self._list_topics_name_sub_selected.append(topic_name)
		self._list_topics_name_sub_selected = list(set(self._list_topics_name_sub_selected))

	def _remove_subscriber_to_variable(self,topic_name):
		if ( (len(self._list_topics_name_sub_selected) != 0 ) and (topic_name in self._list_topics_name_sub_selected) ):
			self._list_topics_name_sub_selected.remove(topic_name)

	def _add_publisher_to_variable(self,topic_name):
		self._list_topics_name_pub_selected.append(topic_name)
		self._list_topics_name_pub_selected = list(set(self._list_topics_name_pub_selected))

	def _remove_publisher_to_variable(self,topic_name):
		if ( (len(self._list_topics_name_pub_selected) != 0) and (topic_name in self._list_topics_name_pub_selected) ):
			self._list_topics_name_pub_selected.remove(topic_name)




class Pub_Sub():#_valider_#-----------------------------
	"""
	This class reads the selected topics and generates python publishers and python subscribers in the current directory.
	Files can be made executable if you do "chmod +x filename"
	"""
    	def __init__(self,genecode):
		self._genecode = genecode
		self._liste_msg_name = []
		self._liste_msg_type = []


	def _open_file(self):
		if (len(self._genecode._topicwidget._interface_pub_sub._name_file) == 0) :
			self.my_file_class = open((self._genecode._topicwidget.workspace_directory.text()+"Command_class.py"),"w")
		else :
			self.my_file_class = open((self._genecode._topicwidget.workspace_directory.text()+(self._genecode._topicwidget.name_line_edit.text().replace(' ','_')+"_class.py")),"w")		

	def _close_all_file(self):
		self.my_file_class.close()
		
	def _clear_file_message_list(self):
		self._liste_msg_name = []
		self._liste_msg_type = []
		for value in self._genecode._list_topics_name_sub_selected:
			self._liste_msg_name.append(value)
		for value in self._genecode._list_topics_name_pub_selected:
			self._liste_msg_name.append(value)
		self._liste_msg_name=list(set(self._liste_msg_name)) #Removes redundancies from messages
		for elem in self._liste_msg_name :
			self._liste_msg_type.append(self._genecode._dict_topics[elem])
		self._liste_msg_type=list(set(self._liste_msg_type)) #Removes redundancies from messages

	def _import_lib(self):
		self.my_file_class.write("#!/usr/bin/env python\n")
		self.my_file_class.write("import rospy\n")
		self._clear_file_message_list()
		for elem in self._liste_msg_type :
			frome = elem[0:elem.find("/")]#Retrieves the first part of the message
			importe = elem[elem.find("/")+1:len(elem)]#Retrieves the second part of the message
			self.my_file_class.write('from {0}.msg import {1}\n'.format(frome,importe))#from ... import ....

	def _my_name_class(self):
		self.my_file_class.write('\nclass Command() :\n'.format())

	def _my_init(self):
		self.my_file_class.write('\tdef __init__(self) :\n'.format())

	def _my_class_attributes(self):
		index = 0
		for elem in self._genecode._list_topics_name_sub_selected :
			type_topic = self._genecode._dict_topics[elem]
			self.my_file_class.write('\t\tself._data{0} = {1}()\n'.format(elem.replace("/","_"),type_topic[type_topic.find("/")+1:len(type_topic)]))
			index = index + 1
		index = 0
		for elem in self._genecode._list_topics_name_sub_selected :
			type_topic = self._genecode._dict_topics[elem]
			self.my_file_class.write('\t\tself.sub{3} = rospy.Subscriber({1}{0}{1}, {2}, self._callback{3})\n'.format(elem,"'",type_topic[type_topic.find("/")+1:len(type_topic)],elem.replace('/','_')))
			index = index + 1
		index = 0
		for elem in self._genecode._list_topics_name_pub_selected :
			type_topic = self._genecode._dict_topics[elem]
			self.my_file_class.write('\t\tself.pub{0} = rospy.Publisher({2}{1}{2}, {3}, queue_size=10)\n'.format(elem.replace("/","_"),elem,"'",type_topic[type_topic.find("/")+1:len(type_topic)]))
			index = index + 1
		
		

	def _information_message(self):
		self.my_file_class.write('#if you want some information about this messages, you can \n#check the following links. The links provide information about \n#the composition of the message.\n\n'.format())
		self._clear_file_message_list()
		for elem in self._liste_msg_type :
			frome = elem[0:elem.find("/")]#Retrieves the first part of the message
			importe = elem[elem.find("/")+1:len(elem)]#Retrieves the second part of the message
			self.my_file_class.write('#{0} => http://docs.ros.org/melodic/api/{1}/html/msg/{0}.html\n'.format(importe,frome))



	def _def_callback_sub(self):
		index=0
		for elem in self._genecode._list_topics_name_sub_selected : 
			self.my_file_class.write('\n\tdef _callback{0}(self,data):\n'.format(elem.replace('/','_'))) 
			self.my_file_class.write('\t\tself._data{0}=data\n'.format(elem.replace("/","_")))
			index = index + 1

	def _def_get_data(self):
		index=0
		for elem in self._genecode._list_topics_name_sub_selected : 
			self.my_file_class.write('\n\tdef _get{0}(self):\n'.format(elem.replace('/','_'))) 
			self.my_file_class.write('\t\treturn self._data{0}\n'.format(elem.replace("/","_")))
			index = index + 1

	def _def_method_pub(self):
		index = 0
		for elem in self._genecode._list_topics_name_pub_selected :
			type_topic = self._genecode._dict_topics[elem]
			self.my_file_class.write('\n\tdef _publish{0}(self,{1}_msgs):\n'.format(elem.replace('/','_'),type_topic[type_topic.find("/")+1:len(type_topic)])) 
			self.my_file_class.write('\t\tself.pub{0}.publish({1}_msgs) #Publish your data\n'.format(elem.replace("/","_"),type_topic[type_topic.find("/")+1:len(type_topic)]))
			index = index+1

	def _def_if_main(self):
		self.my_file_class.write("\nif __name__ == '__main__':\n")
		self.my_file_class.write("\tcommand_node = Command()\n")
		if (len(self._genecode._topicwidget._interface_pub_sub._name_file) == 0) :
			self.my_file_class.write('\trospy.init_node({0}Command_node{0}, anonymous=True)\n'.format("'"))
		else :
			self.my_file_class.write('\trospy.init_node({0}{1}_node{0}, anonymous=True)\n'.format("'",self._genecode._topicwidget._interface_pub_sub._name_file.replace(' ','_')))
		self.my_file_class.write('\trate = rospy.Rate({0})\n'.format(self._genecode._topicwidget._interface_pub_sub._get_frequency()))
		self.my_file_class.write('\twhile not rospy.is_shutdown():\n'.format())
		self.my_file_class.write('\t\t#insert here your use case, don t forget the chmod +x name_of_your_script \n'.format())
		self.my_file_class.write('\t\trate.sleep()\n'.format())

	def _class(self):
		self._information_message()
		self._my_name_class()
		self._my_init()
		self._my_class_attributes()
		self._def_callback_sub()
		self._def_get_data()
		self._def_method_pub()
		self._def_if_main()

	def _generation_code_pub_true_sub_true(self):
		self._open_file()
		self._import_lib()
		self._class()
		self._close_all_file()

	def _generation_code_pub_true_sub_false(self):
		self._open_file()
		self._import_lib()
		self._class()
		self._close_all_file()

	def _generation_code_pub_false_sub_true(self):
		self._open_file()
		self._import_lib()
		self._class()
		self._close_all_file()

	def _generation_code_pub_false_sub_false(self):
		print("Generation code error : Publisher checkbox and subscriber checkbox UNCHECKED, please check at least one\n")
			

	def _generation_code_class_command(self):
		if ( (len(self._genecode._list_topics_name_pub_selected) != 0) and ((len(self._genecode._list_topics_name_sub_selected) != 0))) :
			self._generation_code_pub_true_sub_true()
			
		elif ( (len(self._genecode._list_topics_name_pub_selected) != 0) and ((len(self._genecode._list_topics_name_sub_selected) == 0))) :
			self._generation_code_pub_true_sub_false()

		elif ( (len(self._genecode._list_topics_name_pub_selected) == 0) and ((len(self._genecode._list_topics_name_sub_selected) != 0))) :
			self._generation_code_pub_false_sub_true()

		elif ( (len(self._genecode._list_topics_name_pub_selected) == 0) and ((len(self._genecode._list_topics_name_sub_selected) == 0))) :
			self._generation_code_pub_false_sub_false()


class Node_generation_main():#_valider_#-----------------------------
    	def __init__(self,Pub_sub):
		self._pub_sub = Pub_sub



	def _open_file(self):
		if (len(self._pub_sub._genecode._topicwidget.workspace_directory.text()) == 0) :
			if (len(self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file) == 0):
				self.my_file_main = open("Command_main.py","w")
			else :
				self.my_file_main = open(((self._pub_sub._genecode._topicwidget.name_line_edit.text().replace(' ','_')+"_main.py")),"w")	
			
		else :
			if (len(self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file) == 0):
				self.my_file_main = open((self._pub_sub._genecode._topicwidget.workspace_directory.text()+"Command_main.py"),"w")
			else :
				self.my_file_main = open((self._pub_sub._genecode._topicwidget.workspace_directory.text()+(self._pub_sub._genecode._topicwidget.name_line_edit.text().replace(' ','_')+"_main.py")),"w")	

	def _close_file(self):
		self.my_file_main.close()
	
	def _import_lib(self):
		self.my_file_main.write("#!/usr/bin/env python\n")
		self.my_file_main.write("import rospy\n")
		if (len(self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file) == 0):
			self.my_file_main.write('from Command_class import Command\n'.format())
		else :
			self.my_file_main.write('from {0}_class import Command\n'.format(self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file.replace(" ","_")))
		for elem in self._pub_sub._liste_msg_type :
			frome = elem[0:elem.find("/")]#Retrieves the first part of the message
			importe = elem[elem.find("/")+1:len(elem)]#Retrieves the second part of the message
			self.my_file_main.write('from {0}.msg import {1}\n'.format(frome,importe))#from ... import ....


	def _def_data_msgs(self):
		for elem in self._pub_sub._liste_msg_type :
			self.my_file_main.write('\t_{0}_msgs = {1}()\n'.format(elem[elem.find("/")+1:len(elem)].lower(),elem[elem.find("/")+1:len(elem)]))

	def _information_message(self):
		self.my_file_main.write('#if you want some information about this messages, you can \n#check the following links. The links provide information about \n#the composition of the message.\n\n'.format())
		for elem in self._pub_sub._liste_msg_type :
			frome = elem[0:elem.find("/")]#Retrieves the first part of the message
			importe = elem[elem.find("/")+1:len(elem)]#Retrieves the second part of the message
			self.my_file_main.write('#{0} => http://docs.ros.org/melodic/api/{1}/html/msg/{0}.html\n'.format(importe,frome))

	def _def_if_main(self):
		self.my_file_main.write("\nif __name__ == '__main__':\n")
		self.my_file_main.write("\t_command = Command()\n")
		self._def_data_msgs()
		if (len(self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file) == 0) :
			self.my_file_main.write('\trospy.init_node({0}my_command_node{0}, anonymous=True)\n'.format("'"))
		else :
			self.my_file_main.write('\trospy.init_node({0}{1}{0}, anonymous=True)\n'.format("'",self._pub_sub._genecode._topicwidget._interface_pub_sub._name_file.replace(' ','_')))
		self.my_file_main.write('\trate = rospy.Rate({0})\n'.format(self._pub_sub._genecode._topicwidget._interface_pub_sub._get_frequency()))
		self.my_file_main.write('\twhile not rospy.is_shutdown():\n'.format())
		self.my_file_main.write('\t\t#insert your use case here, don t forget the chmod +x name_of_your_script\n'.format())
		self.my_file_main.write('\t\trate.sleep()\n'.format())


	def _generation_code_main(self):
		self._open_file()
		self._import_lib()
		self._information_message()
		self._def_if_main()
		self._close_file()
























