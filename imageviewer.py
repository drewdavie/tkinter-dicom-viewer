#GUI design based on the following tutorial:
#https://pythonprogramming.net/object-oriented-programming-crash-course-tkinter/?completed=/tkinter-depth-tutorial-making-actual-program/

#This programme opens up images (nominally DICOMs), can scroll through 3D images also.
#For 2D images, can automatically calculate PIU and flatness and symmetry from profiles, although is currently only setup to work when the signal is darker than the background

import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askopenfilenames
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import pydicom
import numpy as np
import image_methods as img_methods
import importlib
importlib.reload(img_methods)
from PIL import Image
import sys, os
import logging
import logging.handlers
import traceback

LARGE_FONT= ("Verdana", 12)

#this block manages cases where we want the cwd but the script has been compiled into an executable
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.getcwd()

if os.path.isdir(application_path + "\\Debug\\") is False:
    os.mkdir(application_path + "\\Debug\\")

LOG_FILENAME = application_path + "\\Debug\\debug.log"
logger = logging.getLogger()
logger.setLevel(logging.ERROR)
fh = logging.FileHandler(LOG_FILENAME)
f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(f_format)
logger.addHandler(fh)

#parentheses on a class indicate inheritance
class ImageViewer(tk.Tk):

    def __init__(self, *args, **kwargs):

        tk.Tk.__init__(self, *args, **kwargs)
        tk.Tk.wm_title(self, "DICOM Viewer")
        
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand = True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

	#create empty dict to fill with frames
        self.frames = {}
        
        for F in (StartPage, ImagePage):

            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)

    def show_frame(self, cont):

        frame = self.frames[cont]
        frame.tkraise()

class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self,parent)
        label = tk.Label(self, text="Start Page", font=LARGE_FONT)
        label.pack(pady=10,padx=10)
        
        button = tk.Button(self, text="ImagePage", command=lambda: controller.show_frame(ImagePage))
        button.pack()     
        
class ImagePage(tk.Frame):
   
    def __init__(self, parent, controller):
    
        tk.Frame.__init__(self, parent)
        label = tk.Label(self, text="Image Viewer", font=LARGE_FONT)
        label.pack(pady=10,padx=10)

        home_button = tk.Button(self, text="Back to Home", command=lambda: controller.show_frame(StartPage))
        home_button.pack()
       
        load_button = tk.Button(self, text="Browse...", command=self.load_file)
        load_button.pack() 
        
        self.f = Figure(figsize=(6,6), dpi=100)
        self.a = self.f.add_subplot(1,1,1)
        self.canvas = FigureCanvasTkAgg(self.f, self)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        #these actions fail on a 3D image (and not gracefully!), could just force them to analyse the current slice
        self.PIU_button = tk.Button(self, text="Calculate PIU", command=lambda: self.get_results(img_methods.PIU))
        self.PIU_button.pack()
        self.profiles_button = tk.Button(self, text="Profiles", command=self.profile_click)
        self.profiles_button.pack()
        
        self.reset_button = tk.Button(self, text="Reset", command=self.plot_image)
        self.reset_button.pack()
                
        # create empty array to allow the buttons to not fail if image hasn't been loaded, can probably be done in a nicer way 
        self.pixels = []
                                           
    def load_file(self):

        try:
            filenames = askopenfilenames(initialdir=application_path, filetypes=(("DICOM Files", "*.dcm"), ("JPEG Files", "*.jpg"), ("TIF Files", "*.tif"), ("PNG Files", "*.png"),  ("All Files", "*.*")), title="Open Image File")
            filenames = list(filenames)
            
            if not filenames:
                return

            self.pixels = []

            for filename in filenames:
            
                if filename.endswith('.dcm'):
                    ds=pydicom.read_file(filename)
                    image = np.asarray(ds.pixel_array)
                    # handle a 3D pixel_array from one file
                    if image.ndim > 2:
                        for im in image:
                            self.pixels.append(im)
                    else:
                        self.pixels.append(image)
                else:
                    #convert image to grayscale so that it can be analysed as a 2D array in just 2D
                    image = Image.open(filename).convert('L')
                    image = np.asarray(image, dtype="int16")
                    self.pixels.append(image)

            self.pixels = np.asarray(self.pixels)
            self.plot_image()

        except Exception as e:
            messagebox.showinfo(title="Unable to Load File", message="Unable to load file, please choose another file or consult the debug log.")
            logger.error(e, exc_info=True)
 
    def plot_image(self):

        if self.pixels.ndim > 2:
            self.plot_slices()
        else:
            self.a.clear()
            self.a.imshow(self.pixels, cmap='gray')       
            self.canvas.draw()

    def plot_slices(self):

        self.slices = self.pixels.shape[0]
        #// performs integer division rather than floating point
        self.ind = self.slices//2
        self.a.clear()
        self.a.imshow(self.pixels[self.ind], cmap='jet')
        self.a.set_xlabel('Slice %s' % self.ind)
        self.canvas.draw()
        self.scroll = self.f.canvas.mpl_connect('scroll_event', self.onscroll)

    def onscroll(self, event):
        
        #if 2D image loaded after 3D image prevent the scrolling functions doing anything while leaving scrolling active
        if self.pixels.ndim < 3:
            return
        
        if (event.button == 'up') and (self.ind < (self.slices - 1)):
            self.ind = (self.ind + 1) % self.slices
            self.update_slice()
        elif (event.button == 'down') and (self.ind > 0):
            self.ind = (self.ind - 1) % self.slices
            self.update_slice()

    def update_slice(self):

        self.a.clear()
        self.a.imshow(self.pixels[self.ind], cmap='jet')
        self.a.set_xlabel('Slice %s' % self.ind)
        self.canvas.draw()
        
    def get_results(self, method):
        #generic function for obtaining a numerical parameter such as uniformity

        try:
            method_name = method.__name__
            result, analysed_pixels = method(self.pixels[self.ind])
            messagebox.showinfo(method_name, method_name + ": " + str(result))
            self.a.clear()
            self.a.imshow(analysed_pixels)       
            self.canvas.draw()
            
        except Exception as e:
                messagebox.showinfo(title="Unable to Perform Analysis", message="Unable to perform analysis, ensure a file is loaded or consult the debug log.")
                logger.error(e, exc_info=True)

    def profile_click(self):

        #activate the clicking, let the onclick event record data, then profiles method processes
        self.cid = self.f.canvas.mpl_connect('button_press_event', self.profile_coords)
        messagebox.showinfo("Profiles", "Click Top, Bottom, Left, then Right to select profile edges.")
        self.coords = []   
        
    def profile_coords(self, event):

        #lets user click and records four sets of coordinates
        ix, iy = event.xdata, event.ydata
        self.coords.append((ix, iy))

        if len(self.coords) > 3:
            self.f.canvas.mpl_disconnect(self.cid)

            try:
                # if a 3D image is loaded get the profile of the current slice
                if self.pixels.ndim < 3:
                    analysed_pixels, horf, hors, verf, vers = img_methods.profiles(self.pixels, self.coords)
                else:
                    analysed_pixels, horf, hors, verf, vers = img_methods.profiles(self.pixels[self.ind], self.coords)
                
                self.a.clear()
                self.a.imshow(analysed_pixels)       
                self.canvas.draw()

                messagebox.showinfo("Profile Results", "Hor F: " + str(horf) + " Hor S: " + str(hors) + " Ver F: " + str(verf) + " Ver S: " + str(vers))

            except Exception as e:
                messagebox.showinfo(title="Unable to Calculate Profiles", message="Unable to calculate profiles, please try again in another area or consult the debug log.")
                logger.error(e, exc_info=True)

app = ImageViewer()
app.mainloop()
