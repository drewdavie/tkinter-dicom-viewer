import numpy as np
import scipy.interpolate as interpolate
import matplotlib.pyplot as plt
    
#https://stackoverflow.com/questions/44865023/circular-masking-an-image-in-python-using-numpy-arrays masking explanation 

def PIU(pixels):

    #create a mask covering a central portion of the circular image, assuming it is centrally positioned
    nrows = pixels.shape[0]
    ncols = pixels.shape[1]
    centre = [nrows/2,ncols/2]
    #5.5 is jut an emperical cut-off for the radius of the mask 
    radius = min(nrows, ncols)/5.5 
    X, Y = np.ogrid[:nrows,:ncols]
    dist_from_centre = np.sqrt((X-centre[0])**2 + (Y-centre[1])**2)
    mask = dist_from_centre <= radius

    masked_pixels = pixels.copy()
    #by setting everything outside the main mask to 0, can assume that our min inside the ROI is > 0 so can be pinned down
    masked_pixels[~mask]=0
    
    #make small mask max/min regions from which we get the mean to calculate the PIU
    maxindices = np.where(masked_pixels  == masked_pixels.max())
    dist_from_max = np.sqrt((X-maxindices[0][0])**2 + (Y-maxindices[1][0])**2)
    maxmask = dist_from_max <=2

    #everything outside of the main mask is 0, so find the minimum nonzero 0 value within the mask
    minindices = np.where(masked_pixels  == min(masked_pixels[np.nonzero(masked_pixels)]))
    dist_from_min = np.sqrt((X-minindices[0][0])**2 + (Y-minindices[1][0])**2)
    minmask = dist_from_min <=2


    #in a very uniform image the maxmean can be lower then the minmean giving a PIU of over 100
    maxmean = pixels[maxmask].mean()
    print(maxmean)
    minmean = pixels[minmask].mean()
    print(minmean)
    PIU = 100*(1-((maxmean-minmean)/(maxmean+minmean)))
    
    #show the main mask used and the location of the max and min masks
    #plt.figure(1)
    #plt.imshow(masked_pixels)
    max_min_pixels = pixels.copy()
    max_min_pixels[maxmask]=5000
    max_min_pixels[minmask]=2500
    #plt.figure(2)
    #plt.imshow(max_min_pixels)
    #plt.show()
    
    #return the pixels with the ROIs identified and show in the window 
    return PIU, max_min_pixels

def profiles(pixels, coords):

        profile_pix = np.copy(pixels)
        #set column with x, row range with y, y2
        x, y, y2 = int(coords[0][0]), int(coords[0][1]), int(coords[1][1])
        #set row with y3, row ranage with x3, x4
        x3, y3, x4 = int(coords[2][0]), int(coords[2][1]), int(coords[3][0])

        print(x, y, y2)
                 
        #show on graph the chosen range
        #take the median profile over a rectangle set dynamically to be 1% of the y range, so artefacts such as dead pixels will be ignored
        width = int(abs(y-y2)*0.01)

        if width == 0:
            width = 1
            
        #set different shades for the profile ranges so that the user can see 
        profile_pix[y:y2,x-width:x+width] = 10
        profile_pix[y3-width:y3+width,x3:x4] = 10

        #copy the selected ranges for each axis
        hor_data = np.copy(pixels[y3-width:y3+width, x3:x4])
        hor_data = np.median(hor_data, axis=0)
        ver_data = np.copy(pixels[y:y2,x-width:x+width])
        ver_data = np.median(ver_data, axis=1)
        
        #process the chosen profile ranges, get three different sections of the range
        hor_prof, hor_fwhm, hor_beam, hor_flatness, hor_symmetry = process_profile(hor_data, "X")
        ver_prof, ver_fwhm, ver_beam, ver_flatness, ver_symmetry = process_profile(ver_data, "Y")
        
        fig = plt.figure()
        ax_x = plt.subplot(1,2,1)
        ax_y = plt.subplot(1,2,2)
        fig.canvas.set_window_title('Profiles')
        ax_x.set_ylabel('Intensity (%)')
        ax_x.set_title('X Profile')
        ax_y.set_title('Y Profile')
        ax_x.plot(hor_prof)
        ax_x.plot(hor_fwhm)
        ax_x.plot(hor_beam)
        ax_y.plot(ver_prof)
        ax_y.plot(ver_fwhm)
        ax_y.plot(ver_beam)
        plt.show(block=False)

        return profile_pix, hor_flatness, hor_symmetry, ver_flatness, ver_symmetry

    
def process_profile(profile, axis):

        #invert and normalise profiles - inversion required for film, could make a check to identify if this is required
        if max(profile) == 0:
            #Print error message, carry on calculating and give zero answer otherwise functions above break
            print("Invalid area selected, no pixel value above 0.")
        else:
            profile = np.divide(profile,max(profile))

        profile[:] = [1-i for i in profile]

        if max(profile) == 0:
            print("Invalid area selected, no pixel value above 0.")
        else:
            profile = np.divide(profile,max(profile))
            

        #interpolate profile over a smaller grid to give more granularity as data is sparse especially in penumbra
        xaxis = np.arange(len(profile))
        #interp acts as interpolation to feed in new grid size
        interp = interpolate.interp1d(xaxis,profile,kind='linear')
        #create the new grid  with 10 times as many points as the original grid, new x points spread between integers
        x_interp = np.linspace(0,len(profile)-1,num=len(profile)*10)
        profile = interp(x_interp)
        
        #find half maximunm on each side: abs difference between points on each side and half maximum, then minimise with argmin
        first_half_max = np.abs(profile[0:int(len(profile)/2)] - max(profile)/2).argmin()
        second_half_max = np.abs(profile[int(len(profile)/2):] - max(profile)/2).argmin() + int(len(profile)/2)
        fwhm = second_half_max-first_half_max

        #generate fwhm and beam for plotting, beam uses middle 80%, so take off 10% at each end
        fwhm_plot = profile[first_half_max:second_half_max]
        beam = profile[first_half_max+int(fwhm/10):second_half_max-int(fwhm/10)]

        #calc flatness
        flatness = 100*((max(beam)-min(beam))/(max(beam)+min(beam)))

        #if useful beam is an odd integer remove a central data point, otherwise the symmetry calculations fail
        #sym_array outputs all of the individual ratios of the data points from each side of the profile to compare with the manual method
        if len(beam) % 2 == 0:
            sym_array = beam[0:int(len(beam)/2)]/np.flip(beam[int(len(beam)/2):len(beam)])
        else:
            beam = np.delete(beam, int(len(beam)/2)+1)
            sym_array = beam[0:int(len(beam)/2)]/np.flip(beam[int(len(beam)/2):len(beam)])

        #calculate symmetry in a different way by summing over the whole area of each profile half and finding the difference
        symmetry = 100*(np.sum(beam[0:int(len(beam)/2)]) - np.sum(beam[int(len(beam)/2):len(beam)]))/(np.sum(beam[0:int(len(beam)/2)]) + np.sum(beam[int(len(beam)/2):len(beam)]))

        #hconcat nans to shift into correct plotting position after the cut off from the first half maximum  
        fwhm_plot = np.concatenate([np.full(first_half_max, np.nan),fwhm_plot])
        beam = np.concatenate([np.full(first_half_max+int(fwhm/10),np.nan),beam])
        
        return profile, fwhm_plot, beam, flatness, symmetry
