# Based on this tutorial: https://www.programiz.com/python-programming/user-defined-exception
# define Python user-defined exceptions
class Error(Exception):
    """Base class for other exceptions"""
    pass

class NotSameFileTypeError(Exception):

    def __init__(self, message="The files chosen are not all of the same file type."):
        self.message = message
        super().__init__(self.message)

class DcmStudyError(Exception):

    def __init__(self, message="DICOM files chosen do not all belong to the same study."):
        self.message = message
        super().__init__(self.message)

class DimError(Exception):

    def __init__(self, message="DICOM pixel data is neither 1 or 2 dimensional."):
        self.message = message
        super().__init__(self.message)
