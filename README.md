Application Name - Hogslice

Clear problem statement - Convert .stl and .step files into gcode the hogforge machine can interpret (GCODE)

Objectives - Create an application that can manipulate a 3D file in an enviroment, and convert its coordinates into gcode for a 2D gantry machine 
------------------------------------
Functional Requirments - 

Application must be able to import a 3d-based image, including STEP STL

Must be able to drag and drop 3d based files, and render it inside the sofware

System must also contain a axis based control system. Containing xyz and angle based rotations for these 3d based objects


System also must render a static 3d image of the build chamber, including the accurate dimensions of its square chamber

The system must be able to contain a slicer, in which renders the division of each layer into gcode

The slicer must be able to contain an infill function, that allows for specific

Must also contain a sidebar, in which has a list of all avaliable 3d images (excluding the build chamber) for ease of access

The sidebar must be able to manipulate and display data given the current selection, hide & select objects, as well as right-click functionality 

Right click on a selected option must display additional methods as shown from Prusa3D.




Nonfunctional Requirements - 

Application must have settings to allow for changing laser and buildplate sizing 

Export to USB functionality must be placed when device is sliced

Application must save workspaces for current settings and presets

Structure --

                    main.py/QtWindow -- Build Window here
                       |
            ------------------------------------------------------------------------------------- 
                |                                          |                     |
            WindowManager                                  |                     |
                |                                          |                     |
            -----------                                    |                     |              
            |          |                                    |                    |
            |          |                                    |                    |               
        vtkManager     |                                   Gcode Creator      Settings      
            |          |                                                         | 
            |          |                                                         |
            |          |                                            Machine--------------Presets
            |          |                                                |
            |          |                                          --------------
            |        Superclass(QT Widget) -- addObjct             |           |
            |           |                                      Laser          Chamber
            |                                               
            |        Button - ComboBox, Checkbox            
            |                                               
            |                                         

            |
            |
            |
        Superclass(VTKObject) ------------------------------Slicer Generator -- generate each row and pattern
                                                                
            |Integrate other new objects easily here            
    -----------------------------------                         
    |                 |                |                    
GizmoControl      Main Chamber     STLManager
