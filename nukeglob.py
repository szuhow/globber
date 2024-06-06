#!/bin/env python3
import glob
import os
import argparse
import logging
import datetime
import re
from pathlib import Path

class FileSearcher:
    """
    A class for searching files in a directory and its subdirectories.

    Args:
        args (object): An object containing the command-line arguments.

    Attributes:
        search_dir (str): The directory to search for files.
        date (datetime.datetime): The date to filter files by creation time.
        contain (str): The substring to filter files by.
        found_flag (bool): Flag indicating whether to display found files.
        not_found_flag (bool): Flag indicating whether to display files not found.

    Methods:
        find_node: Find nodes in nk file.
        search_files: Search for files in the text.
        _extract_file_path: Extract the file path from a given path.
        _handle_sequence_pattern: Handle file paths with sequence patterns.
        _handle_non_sequence_pattern: Handle file paths without sequence patterns.
        filter_token: Filter found and not found files by a given substring.
        get_first_file_in_sequence: Get the first file in a file sequence.
        print_files: Print the found and not found files.
        search: Perform the file search.
    """
    def __init__(self, args):
        self.search_dir = args.directory
        self.date = args.date
        self.contain = args.contain
        self.found_flag = args.hide_found
        self.not_found_flag = args.hide_not_found

        
    def find_node(self, text, node_name):
        pattern = fr"{node_name} \{{([^}}]*)\}}"
        matches = re.findall(pattern, text, re.DOTALL)
        nodes = []
        for match in matches:
            properties = match.split('\n')
            node = {}
            for prop in properties:
                if prop.strip():
                    key, value = prop.strip().split(' ', 1)
                    node[key] = value
            nodes.append(node)
        return nodes

    def search_files(self, text):
        found = []
        not_found = []
        read_nodes = self.find_node(text, "Read")
        for node in read_nodes:
            if 'file' in node:
                file_path = node['file'].strip('"')
                if file_path.startswith('\\[join'):
                    continue
                found_files, not_found_files = self._extract_file_path(file_path)
                if found_files:
                    found.append(found_files)
                if not_found_files:
                    not_found.append(not_found_files)
        return found, not_found

    def _extract_file_path(self, path):
        path = Path('/' + '/'.join(Path(path).parts[1:]))
        sequence_pattern = re.search(r'(%\d+d|\#{2,})', str(path))

        if sequence_pattern:
            return self._handle_sequence_pattern(path)
        else:
            return self._handle_non_sequence_pattern(path)

    def _handle_sequence_pattern(self, path):
        directory = path.parent
        file_name = re.sub(r'(%\d+d|\#{2,}).exr', '*', path.name)
        matching_files = sorted(list(directory.glob(file_name)))

        if matching_files:
            return str(path), ""
        else:
            return "", str(path)

    def _handle_non_sequence_pattern(self, path):
        directory = path.parent

        try:
            files = os.listdir(directory)
        except FileNotFoundError:
            return "", str(path)

        if path.name in files:
            return str(path), ""
        else:
            return "", str(path)
        

    def filter_token(self, found, not_found):
        if self.contain:
            tokens = self.contain.split('/')
            found = [path for path in found if all(token in str(path) for token in tokens)]
            not_found = [path for path in not_found if all(token in str(path) for token in tokens)]
        return found, not_found


    def get_first_file_in_sequence(self, path):
        """If the path represents a file sequence, return the first file in the sequence."""
        if '%' in path or '#' in path:  # Check if path is a sequence
            sequence_pattern = re.compile(r'(%\d+d|\#{2,})')
            path = sequence_pattern.sub('*', path)
            sequence_files = sorted(glob.glob(path))
            if sequence_files:  # If there are matching files
                return sequence_files[0]  # Get the first file
        return path


    def print_files(self, found, not_found):
        if self.not_found_flag:
            print("\nFiles not found:")
            for path in not_found:
                print(path)
        if self.found_flag:
            print("Files found:")
            if self.date:
                modified_found = []
                for path in found:
                    path = self.get_first_file_in_sequence(path)
                    if datetime.datetime.fromtimestamp(os.path.getctime(path)) < self.date:
                        modified_found.append((path, os.path.getctime(path)))
                for path in modified_found:
                    print(f"{path[0]} (created: {datetime.datetime.fromtimestamp(path[1])})")
            else:
                for path in found:
                    print(path)


    def search(self):    
        for dirpath, dirnames, filenames in os.walk(self.search_dir):
            dirnames[:] = [d for d in dirnames if not d[0] == '.']
            for filename in glob.glob(os.path.join(dirpath, '*.nk')):
                print(f"-------------------------------")
                print(f"Found .nk file: {filename}")
               
                with open(filename, 'r') as file:
                    text = file.read()
                    found, not_found = self.search_files(text)
                    found, not_found = self.filter_token(found, not_found)
                    self.print_files(found, not_found)

    
def main():
    # # Configure logging
    # logging.basicConfig(level=logging.DEBUG)

    # Create argument parser
    parser = argparse.ArgumentParser(description='Search for file paths in Read nodes in .nk files in a directory.')
    parser.add_argument('directory', help='The directory to search.')
    parser.add_argument('--date', default=None, help='Filter files older than the specified date (YYYY-MM-DD)', type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'))
    parser.add_argument('--contain', default=None, help='Filter files that contain the specified path tokens.')
    parser.add_argument('--hide-found', action='store_false', help='Hide files that are found.')
    parser.add_argument('--hide-not-found', action='store_false', help='Hide files that are not found.')

    # Parse arguments
    args = parser.parse_args()
    searcher = FileSearcher(args)
    searcher.search()

if __name__ == "__main__":
    main()
