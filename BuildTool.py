import sublime, sublime_plugin

import subprocess
import types
import re
import os

from xml.etree import ElementTree as ET
from urllib import urlopen

GOOGLE_AC = r"http://google.com/complete/search?output=toolbar&q=%s"


count = 0;

def formatSignature(sig):
    fmt = re.sub("->",",", sig)
    fmt = re.sub("(.*), ([A-Za-z0-9]+$)","(\\1):\\2", fmt)
    fmt = re.sub("\s", "", fmt)
    fmt = re.sub(",",", ", fmt)

    return fmt


last_build_cmd = None

previous_builds = {}

# Perform Previous Build
class HaxeBuildCommand(sublime_plugin.WindowCommand):
    def run(self):
        global last_build_cmd
        print "Preparing"
        if last_build_cmd != None:
            projectPath = self.window.folders()[0]
            self.window.run_command("save_all");
            self.window.run_command("exec",{"cmd": last_build_cmd, "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" })
        else:
            print "No default build"

# Choose Build
class HaxeBuildToolCommand(sublime_plugin.WindowCommand):
    mode_types = ["debug","release"]
    os_types = ["mac","flash"]

    cur_mode = ""           #debug or release
    cur_type = ""           #nmml or hxml
    cur_cfg = ""            #something.nmml or something.hxml
    cur_os = ""             #mac flash

    nmmls = []
    hxmls = []
    def run(self):
        self.nmmls = self.get_list_ext("nmml")
        self.hxmls = self.get_list_ext("hxml")

        #self.gen_mru_prompt()
        self.mru_build()

    def mru_build(self):
        global previous_builds
        items = [["Last build","Sample Custom build"], ["Custom build","New ant/nmml/hxml build"]]

        for build in previous_builds:
            s = ""
            for bpart in previous_builds[build]:
                s += bpart + " "
            items.append( s )

        def _callback(idx):
            if idx == -1:
                return
            elif items[idx][0] == "Last build":
                self.window.run_command("haxe_build")
            elif items[idx][0] == "Custom build":
                self.type_build()
            else:
                projectPath = self.window.folders()[0]
                self.window.run_command("save_all");
                self.window.run_command("exec",{"cmd": previous_builds[idx-2], "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" }) 
            return

        self.window.show_quick_panel (items, _callback)

    def type_build(self):
        items = ["Ant", "Hxml"] #, "Nmml"]

        def _callback(idx):
            if idx == -1:
                return
            elif items[idx] == "Ant":
                print "ANT"
                self.menu_antbuild()
            elif items[idx] == "Hxml":
                print "HXML"
                self.menu_hxml_build()
            #elif items[idx] == "Nmml":
            #    print "NMML"
            return

        self.window.show_quick_panel (items, _callback)

    def menu_hxml_build(self):
        items = self.hxmls

        def _callback(idx):
            global last_build_cmd, previous_builds
            if idx == -1:
                return
            else:
                projectPath = self.window.folders()[0]

                #Make sure to run this under self.window!!!! (not view)
                print "hxml: " + str(items[idx])
                last_build_cmd = ["haxe",items[idx]]
                previous_builds[str(last_build_cmd)] = last_build_cmd
                self.window.run_command("exec",{"cmd": last_build_cmd, "working_dir" : projectPath, "file_regex": "(.+):([0-9]+): characters ([0-9]+-[0-9]+) : (.*)$" })
                
            return

        self.window.show_quick_panel(items, _callback)


    def menu_antbuild(self):

        items = ["Launch","Filler"]

        def _callback(idx):
            global last_build_cmd, previous_builds
            if idx == -1:
                return
            elif items[idx] == "Launch":
                projectPath = self.window.folders()[0]

                #Make sure to run this under self.window!!!! (not view)
                last_build_cmd = ["ant"]
                previous_builds[str(last_build_cmd)] = last_build_cmd
                self.window.run_command("exec",{"cmd":last_build_cmd, "working_dir" : projectPath })
                
            elif items[idx] == "Other targets....":
                print "Filler!"
            return

        self.window.show_quick_panel(items, _callback)

    def gen_mru_prompt(self):
        oplist = []
        if self.cur_cfg != "":
            if self.cur_mode != "":
                oplist.append(["Last Build", self.cur_cfg + " " + self.cur_mode])
        
        oplist.append(["New Build"])
                
        self.window.show_quick_panel(oplist, self.process_mru)

        print dir(self.window)

    def process_mru(self, idx):
        print str(idx)
        if idx == -1:
            return

        if self.cur_cfg != "":
            if self.cur_mode != "":
                if idx == 0:
                    self.build_current()
                    return

        self.gen_nmml_prompt()

    def gen_nmml_prompt(self):
        self.window.show_quick_panel(self.nmmls, self.gen_nmml_debug_prompt)

    def gen_nmml_debug_prompt(self, idx):
        if idx == -1:
            return

        self.cur_cfg = self.nmmls[idx]
        self.cur_type = "nmml"
        self.window.show_quick_panel(["Debug","Release"], self.gen_nmml_platform_prompt)

    def gen_nmml_platform_prompt(self, idx):
        if idx == -1:
            return

        self.cur_mode = self.mode_types[idx]
        self.window.show_quick_panel(["Mac","Flash"], self.sel_mode)

    def sel_mode(self, idx):
        if idx == -1:
            return

        self.cur_os = self.os_types[idx]

        self.build_current()



    def build_current(self):
        cmd = ""
        if self.cur_type == "nmml":
            cmd = "haxelib run nme test " + self.cur_cfg + " " + self.cur_os + " "
            if self.cur_mode == "debug":
                cmd += "-Ddebug"
            
        elif self.cur_type == "hxml":
            True
        else:
            print "cur_type is an invalid value: " + self.cur_type

        #self.window.active_view().run_command("haxe_build",{"cmd":cmd})

        projectPath = self.window.folders()[0]
        self.window.active_view().run_command("exec",{"cmd":cmd, "working_dir" : projectPath})

    def get_list_ext(self, ext):
        projectPath = self.window.folders()[0]

        files = os.listdir(projectPath)
        print "dir: " + str(files)

        pf = [];

        for file in files:
            if self.has_ext(file, ext):
                pf.append(file)

        return pf

    def has_ext(self, s, ext):
        match = re.match(".*\."+ext+"$", s)
        if match is not None:
            return True
        return False
