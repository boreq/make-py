#!/usr/bin/env python
import os, argparse, json, sys, logging

class ToolData(object):
    def __init__(self, chain_element, next_chain_element):
        self.tool = chain_element['tool']
        self.ext_in = chain_element['extension']
        if next_chain_element is not None:
            self.ext_out = next_chain_element['extension']
        else:
            self.ext_out = None

class ChainLink(object):
    def __init__(self, path_in, path_out, tool_data):
        self.path_in = path_in
        self.path_out = path_out
        self.tool_data = tool_data

    def get_tool(self):
        return self.tool_data.tool

def replace_extension(file_path, current_ext, future_ext):
    return file_path[:-len(current_ext)] + future_ext

def get_full_path(file_path):
    return os.path.abspath(os.path.join(makefile_dir, makefile_data['path'], file_path))

def find_tool(file_path):
    """Finds out how to convert a file."""
    next_chain_element = None

    for chain in makefile_data['chains']:
        for chain_element in reversed(chain):
            if file_path.endswith(chain_element['extension']): 
                return ToolData(chain_element, next_chain_element)
            next_chain_element = chain_element

    return None

def get_conversion_chain(path_in):
    """Get all stages of conversion for the given file (all paths one by one)."""
    chain = []

    while True:
        tool_data = find_tool(path_in)
        if tool_data.tool is None:
            break
        path_out = replace_extension(path_in, tool_data.ext_in, tool_data.ext_out)
        chain.append(ChainLink(path_in, path_out, tool_data))
        path_in = path_out

    return chain

def process_file(path_in):
    """Applies all specified conversion steps to a file and returns its final name."""
    logging.debug('Process %s', path_in)
    sys.stdout.write('*')

    conversion_chain = get_conversion_chain(path_in)

    if len(conversion_chain) == 0:
        return path_in

    for chain_link in conversion_chain:
        logging.debug('Convert %s to %s using %s' % (chain_link.path_in, chain_link.path_out, chain_link.get_tool()))
        sys.stdout.write('*')
        command = chain_link.get_tool() % (get_full_path(chain_link.path_in), get_full_path(chain_link.path_out))
        logging.debug(command)
        if not args.dryrun:
            if os.system(command) != 0:
                sys.exit(1)

    # Return the path of the last output file.
    return conversion_chain[-1].path_out

def get_intermediate_files(file_path):
    """Get the list intemediate files created during conversion."""
    return [chain_link.path_out for chain_link in get_conversion_chain(file_path)]

def handle(task):
    final_files = []

    # Process files (create all intermediate files to produce the final output files).
    for path_in in task['input']:
        final_files.append(process_file(path_in))

    # Concat the final output files.
    sys.stdout.write(' > ')

    final_files = [get_full_path(file_path) for file_path in final_files]
    command = 'cat %s > %s' % (' '.join(final_files), get_full_path(task['output']))
    logging.debug(command)
    if not args.dryrun:
        if os.system(command) != 0:
            sys.exit(1)

    # Remove all intermediate files to clean up.
    for file_path in task['input']:
        for intermediate_file in get_intermediate_files(file_path):
            remove_path = get_full_path(intermediate_file)
            sys.stdout.write('-')
            logging.debug('Remove %s', intermediate_file)
            logging.debug('Remove path %s', remove_path)
            if not args.dryrun:
                try:
                    os.remove(remove_path)
                except:
                    pass

# Parse the arguments.
parser = argparse.ArgumentParser()
parser.add_argument('-m', '--makefile', help='Path to a makefile relative to the current working directory.', default='makefile.json')
parser.add_argument('--dryrun', help='Don\'t execute any commands.', action='store_true')
parser.add_argument('--verbosity', help='', default='warning', choices=['critical', 'error', 'warning', 'info', 'debug'])
args = parser.parse_args()

# Configure logging.
numeric_level = getattr(logging, args.verbosity.upper(), None)
logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=numeric_level)

# Set the path to the makefile and its directory.
makefile_path = os.path.join(os.getcwd(), args.makefile)
makefile_dir = os.path.dirname(makefile_path)

# Load json data.
with open(makefile_path, 'r') as f:
    makefile_data = json.load(f)

logging.debug('Passed arguments %s', args)
logging.debug('makefile_path %s', makefile_path)
logging.debug('makefile_dir %s', makefile_dir)

for task in makefile_data['tasks']:
    handle(task)
    sys.stdout.write('\n')
