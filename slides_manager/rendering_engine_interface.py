#  Copyright (c) 2019, CRS4
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy of
#  this software and associated documentation files (the "Software"), to deal in
#  the Software without restriction, including without limitation the rights to
#  use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
#  the Software, and to permit persons to whom the Software is furnished to do so,
#  subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
#  FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
#  COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
#  IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
#  CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from abc import ABCMeta, abstractmethod
import os
import logging

from ..ome_data.original_files import get_original_file
from ..ome_data.projects_datasets import get_fileset_highest_resolution

from .. import settings


class RenderingEngineInterface(object):

    __metaclass__ = ABCMeta

    def __init__(self, image_id, connection):
        self.connection = connection
        self.image_id = image_id
        self.logger = logging.getLogger(__name__)

    # if get_biggest_in_filest is True, return the image with the highest resolution in the fileset
    # of the image with ID image_id, if False simply return image with ID image_id
    def _get_image_object(self, get_biggest_in_fileset=False):
        img = self.connection.getObject('Image', self.image_id)
        if img is None:
            return None
        if get_biggest_in_fileset:
            return get_fileset_highest_resolution(img, self.connection)
        else:
            return img

    def _get_path_from_image_obj(self):
        img = self._get_image_object()
        if img is None:
            return None
        else:
            return os.path.join(
                settings.IMGS_REPOSITORY,
                settings.IMGS_FOLDER,
                img.getImportedImageFilePaths()['server_paths'][0]
            )

    def _get_path_from_original_file_obj(self, file_mimetype):
        ofile = get_original_file(self.connection, self.image_id, file_mimetype)
        if ofile is None:
            return None
        else:
            return ofile.getPath()

    def _get_image_path(self, original_file_source=False, file_mimetype=None):
        if original_file_source:
            return self._get_path_from_original_file_obj(file_mimetype)
        else:
            return self._get_path_from_image_obj()

    def _check_source_type(self, original_file_source):
        pass

    @abstractmethod
    def _get_image_mpp(self, original_file_source=False, file_mimetype=None):
        pass

    @abstractmethod
    def get_openseadragon_config(self, original_file_source=False, file_mimetype=None):
        pass

    @abstractmethod
    def get_slide_bounds(self, original_file_source=False, file_mimetype=None):
        pass

    @abstractmethod
    def get_dzi_description(self, original_file_source=False, file_mimetype=None, tile_size=None):
        pass

    @abstractmethod
    def _get_original_file_json_description(self, resource_path, file_mimetype=None, tile_size=None, limit_bounds=None):
        pass

    def _get_json_description(self, resource_path, img_height, img_width, tile_size=None):
        tile_size = tile_size if tile_size is not None else settings.DEEPZOOM_TILE_SIZE
        return {
            'Image': {
                'xmlns': 'http://schemas.microsoft.com/deepzoom/2008',
                'Url': resource_path,
                'Format': str(settings.DEEPZOOM_FORMAT),
                'Overlap': str(settings.DEEPZOOM_OVERLAP),
                'TileSize': str(tile_size),
                'Size': {
                    'Height': str(img_height),
                    'Width': str(img_width)
                }
            }
        }

    def get_json_description(self, resource_path, original_file_source=False, file_mimetype=None, tile_size=None):
        self._check_source_type(original_file_source)
        if not original_file_source:
            img = self._get_image_object(get_biggest_in_fileset=True)
            if img:
                return self._get_json_description(resource_path, img.getSizeY(), img.getSizeX(), tile_size)
            else:
                return None
        else:
            return self._get_original_file_json_description(resource_path, file_mimetype, tile_size,
                                                            settings.DEEPZOOM_LIMIT_BOUNDS)

    def get_image_description(self, resource_path, original_file_source=False, file_mimetype=None, tile_size=None):
        return {
            'image_mpp': self._get_image_mpp(original_file_source, file_mimetype),
            'tile_sources': self.get_json_description(resource_path, original_file_source,
                                                      file_mimetype, tile_size),
            'slide_bounds': self.get_slide_bounds(original_file_source, file_mimetype)
        }

    @abstractmethod
    def get_thumbnail(self, size, original_file_source=False, file_mimeype=None):
        pass

    @abstractmethod
    def get_tile(self, level, column, row, original_file_source=False, file_mimetype=None, tile_size=None):
        pass
