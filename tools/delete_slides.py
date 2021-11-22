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

import requests
from argparse import ArgumentParser
import os
from shutil import rmtree
import sys
from urllib.parse import urljoin
import logging


class SlidesDeleter(object):

    def __init__(self, ome_base_url, slides_file_list, log_level='INFO', log_file=None):
        self.ome_delete_url = urljoin(ome_base_url, 'mirax/delete_files/')
        self.ome_get_file_info_url = urljoin(ome_base_url, 'file/info/')
        self.slides_list = self.get_slides_list(slides_file_list)
        self.logger = self.get_logger(log_level, log_file)
        self.INDEX_FILE_MT = 'mirax/index'
        self.DATA_FOLDER_MT = 'mirax/datafolder'

    def get_logger(self, log_level='INFO', log_file=None, mode='a'):
        LOG_FORMAT = '%(asctime)s|%(levelname)-8s|%(message)s'
        LOG_DATEFMT = '%Y-%m-%d %H:%M:%S'

        logger = logging.getLogger('slides_deleter')
        if not isinstance(log_level, int):
            try:
                log_level = getattr(logging, log_level)
            except AttributeError:
                raise ValueError('Unsupported literal log level: %s' % log_level)
        logger.setLevel(log_level)
        logger.handlers = []
        if log_file:
            handler = logging.FileHandler(log_file, mode=mode)
        else:
            handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATEFMT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def get_slides_list(self, slides_list_file):
        with open(slides_list_file) as f:
            return [row.replace('\n', '') for row in f]

    def _get_file_path(self, file_name, mimetype):
        response = requests.get(urljoin(self.ome_get_file_info_url, '%s/' % file_name),
                                {'mimetype': mimetype})
        if response.status_code == requests.codes.OK:
            return response.json()['file_path']
        else:
            return None

    def _delete_file(self, file_path, is_folder=False):
        self.logger.info('## DELETING FROM DISK file %s' % file_path)
        try:
            if not is_folder:
                os.remove(file_path)
            else:
                rmtree(file_path)
        except OSError:
            self.logger.warn('File does not exist')

    def _delete_original_file(self, file_name):
        self.logger.info('## DELETING ORIGINAL FILE from OMERO %s' % file_name)
        response = requests.get(urljoin(self.ome_delete_url, '%s/' % file_name))
        if response.status_code != requests.codes.OK:
            self.logger.warn('RESPONSE CODE %s', response.status_code)
            self.logger.warn('%s', response.text)
            return False
        else:
            return True

    def run(self, delete_files=False):
        self.logger.info('STARTING DELETION JOB')
        for slide in self.slides_list:
            if delete_files:
                try:
                    file_path = self._get_file_path(slide, self.INDEX_FILE_MT)
                    folder_path = self._get_file_path(slide, self.DATA_FOLDER_MT)
                except TypeError:
                    # if TypeError -> there is no file with that name on the server
                    self.logger.warn('There is no file with name %s on the server', slide)
                    continue
            deleted = self._delete_original_file(slide)
            if delete_files and deleted:
                self._delete_file(file_path)
                self._delete_file(folder_path, is_folder=True)
        self.logger.info('DELETION JOB COMPLETED')


def get_parser():
    parser = ArgumentParser('Delete Original File objects from OMERO and, optionally, from disk')
    parser.add_argument('--files-list', type=str, required=True,
                        help='the list containing the names of the files that will be deleted')
    parser.add_argument('--ome-base-url',  type=str, required=True,
                        help='the base URL of the OMERO.web server')
    parser.add_argument('--delete', action='store_true',
                        help='also delete files from disk')
    parser.add_argument('--log-level', type=str, default='INFO',
                        help='log level (default=INFO)')
    parser.add_argument('--log-file', type=str, default=None,
                        help='log file (default=stderr)')
    return parser


def main(argv):
    parser = get_parser()
    args = parser.parse_args(argv)
    deleter = SlidesDeleter(args.ome_base_url, args.files_list, args.log_level,
                            args.log_file)
    deleter.run(args.delete)


if __name__ == '__main__':
    main(sys.argv[1:])
