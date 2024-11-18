from pyexiv2 import Image

import os
import shutil
import platform
from time import strftime, localtime
from collections import defaultdict

import dearpygui.dearpygui as dpg

### global vars
yearDict = defaultdict(lambda: defaultdict(list))
invalid_files = []


### helper functions
def writeToLogFile():
  # add processed files to log
  log_contents = "====================\nProcessed Files Summary\n====================\n"
  log_contents += yearDictSummary()
  log_contents += "====================\n\n"

  # add invalid / unprocessed files to log
  log_contents += "====================\n"
  log_contents += f"Invalid / Unprocessed Files ({len(invalid_files)}):\n"
  for file, invalid_reason in invalid_files:
    log_contents += f"  {file}\n    {invalid_reason}\n"
  log_contents += "===================="
  
  # write to file
  f = open("media_sort_log.txt", "w")
  f.write(log_contents)
  f.close()

def printYearDict(dictionary):
  for x in dictionary:
    print(x)
    for y in dictionary[x]:
        print(f"  {y}:")
        for z in dictionary[x][y]:
          print(f"    {z}")

def yearDictSummary():
  ret = ""
  for x in yearDict:
    ret += f"{x}\n"
    for y in yearDict[x]:
      ret += f"  {y}\n    {len(yearDict[x][y])} items\n"
  return ret

def isPhoto(filepath: str):
  photo_file_formats = {".ARW", ".CR2", ".CR3", ".NEF", ".JPG", ".JPEG"}
  
  split_tup = split_tup = os.path.splitext(filepath)
  return split_tup[1] in photo_file_formats

def isVideo(filepath: str):
  video_file_formats = {".MP4", ".AVI", ".MPG", ".MPEG"}

  split_tup = split_tup = os.path.splitext(filepath)
  return split_tup[1] in video_file_formats

def getMediaDate(filepath: str) -> str:
  # reads EXIF data from image and returns the date created
  if isPhoto(filepath):
    try:
      img = Image(filepath)
      data = img.read_exif()
      img_datetime = data.get("Exif.Image.DateTime")
      img.close()
      return img_datetime
    except Exception:
      return "Error getting media date."
  # reads the file properties of video file and returns the date created
  elif isVideo(filepath):
    img_datetime = ""
    if platform.system() == 'Windows':
        img_datetime = os.path.getctime(filepath)
    else: # MacOS
        stat = os.stat(filepath)
        try:
            img_datetime = stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            img_datetime = stat.st_mtime
    # the time above is returned as Epoch seconds, so we convert to a human readable format
    img_datetime = strftime('%Y-%m-%d %H:%M:%S', localtime(img_datetime))
    return img_datetime

### file processing functions
def generateSortSummary(root_dir: str):
  for root, dirs, files in os.walk(root_dir):
    # path = root.split(os.sep)
    for file in files:
        # skip DS_Store files
        if file == ".DS_Store":
          continue
        
        # get full filepath
        full_filepath = os.path.join(os.path.abspath(root), file)
        
        # sort file into year / photo-video dictionary
        media_datetime = getMediaDate(full_filepath)
        media_year = media_datetime[:4]
        if isPhoto(full_filepath):
          yearDict[media_year]["Photos"].append(full_filepath)
        elif isVideo(full_filepath):
          yearDict[media_year]["Videos"].append(full_filepath)
        else:
          invalid_files.append((full_filepath, "Not a photo or video."))
  
  return yearDictSummary()

def sortFiles(root_dir):
  for year, types in yearDict.items():
    year_folder = os.path.join(root_dir, year)
    
    # Create the year folder if it doesn't exist
    os.makedirs(year_folder, exist_ok=True)
    
    for file_type, files in types.items():
      type_folder = os.path.join(year_folder, file_type)
      
      # Create the type folder if it doesn't exist
      os.makedirs(type_folder, exist_ok=True)

      for file_path in files:
        if os.path.isfile(file_path):
          try:
            # Move the file to the appropriate folder
            shutil.move(file_path, type_folder)
            # print(f"Moved: {file_path} -> {type_folder}")
          except Exception as e:
              invalid_files.append((file_path, e))
              print(f"Failed to move {file_path}: {e}")
  writeToLogFile()

def deleteEmptyDirectories(base_directory):
  for dirpath, dirnames, filenames in os.walk(base_directory, topdown=False):
    if not dirnames and not filenames:
      try:
        os.rmdir(dirpath)
        print(f"Deleted empty directory: {dirpath}")
      except OSError as e:
        print(f"Error deleting {dirpath}: {e}")

def main():
  dpg.create_context()

  def directorySelectionCallback(_: str, app_data: dict):
    # Set selected directory
    selected_directory = app_data['file_path_name']
    dpg.set_value("directory_text", f"Selected Directory: {selected_directory}")

    # Run preprocessing
    dpg.set_value("summary_text", "Sorted Folder Structure:\n\n" + generateSortSummary(selected_directory) + "\n\n")
    dpg.configure_item("summary_text", show=True)

    # Show confirmation button
    dpg.configure_item("confirm", show=True)
    dpg.configure_item("close", show=True)

  def confirmCallback():
    selected_directory = dpg.get_value("directory_text").replace("Selected Directory: ", "")
    if selected_directory:
      sortFiles(selected_directory)
    
    # Show confirmation and reset directory
    dpg.set_value("summary_text", "Sorted all files!")
    dpg.configure_item("confirm", show=False)
    dpg.configure_item("close", show=False)
    dpg.configure_item("deleteEmpties", show=True)

  def deleteCallback():
    selected_directory = dpg.get_value("directory_text").replace("Selected Directory: ", "")
    if selected_directory:
      deleteEmptyDirectories(selected_directory)
    
    dpg.set_value("directory_text", "")
    dpg.set_value("summary_text", "")
    dpg.configure_item("deleteEmpties", show=False)

  def close_app():
    dpg.stop_dearpygui()

  dpg.add_file_dialog(
    directory_selector=True, show=False, callback=directorySelectionCallback, tag="file_dialog", width=800 ,height=500)

  with dpg.window(label="Media Sorter", tag="Media Sorter"):
    dpg.add_text("Select a directory to see a summary of the sorted file structure.")
    dpg.add_button(label="Directory Selector", callback=lambda: dpg.show_item("file_dialog"))
    dpg.add_text("", tag="directory_text")
    dpg.add_separator()
    dpg.add_text("Sorted Folder Structure:", tag="summary_text", show=False)
    with dpg.group(horizontal=True):
      dpg.add_button(label="Confirm and Sort Files", tag="confirm", callback=confirmCallback, show=False)
      dpg.add_button(label="Cancel", tag="close", callback=close_app, show=False)
    dpg.add_button(label="Delete Empty Directories?", tag="deleteEmpties", callback=deleteCallback, show=False)

  dpg.create_viewport(title='Media Sorter')
  dpg.setup_dearpygui()
  dpg.show_viewport()
  dpg.set_primary_window("Media Sorter", True)
  dpg.start_dearpygui()
  dpg.destroy_context()

if __name__ == "__main__":
  main()