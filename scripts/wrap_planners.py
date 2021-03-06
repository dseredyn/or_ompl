#!/usr/bin/env python

# Copyright (c) 2014, Carnegie Mellon University
# All rights reserved.
# 
# Authors: Michael Koval <mkoval@cs.cmu.edu>
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
# 
#   Redistributions of source code must retain the above copyright
#   notice, this list of conditions and the following disclaimer.
# 
#   Redistributions in binary form must reproduce the above copyright
#   notice, this list of conditions and the following disclaimer in the
#   documentation and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function
import argparse, yaml, os.path, sys

factory_frontmatter = """\
#include <map>
#include <string>
#include <boost/assign/list_of.hpp>
{includes:s}
#include "PlannerRegistry.h"

namespace or_ompl {{
namespace registry {{

struct BasePlannerFactory {{
    virtual ~BasePlannerFactory() {{ }}
    virtual ompl::base::Planner *create(ompl::base::SpaceInformationPtr space) = 0;
}};

/*
 * Planner Factories
 */\
"""
factory_template = """\
struct {name:s}Factory : public virtual BasePlannerFactory {{
    virtual ompl::base::Planner *create(ompl::base::SpaceInformationPtr space)
    {{
        return new {qualified_name:s}(space);
    }}
}};
"""

registry_frontmatter = """\
/*
 * Planner Registry
 */
typedef std::map<std::string, BasePlannerFactory *> PlannerRegistry;

// The dynamic_cast is necessary to work around a type inference bug when
// using map_list_of on a polymorphic type.
static PlannerRegistry registry = boost::assign::map_list_of\
"""
registry_entry = '    ("{name:s}", dynamic_cast<BasePlannerFactory *>(new {name:s}Factory))'
registry_backmatter = """\
    ;

std::vector<std::string> get_planner_names()
{
    std::vector<std::string> names;
    names.reserve(registry.size());

    PlannerRegistry::const_iterator it;
    for (it = registry.begin(); it != registry.end(); ++it) {
        names.push_back(it->first);
    }

    return names;
}

ompl::base::Planner *create(std::string const &name,
                            ompl::base::SpaceInformationPtr space)
{
    PlannerRegistry::const_iterator const it = registry.find(name);
    if (it != registry.end()) {
        return it->second->create(space);
    } else {
        throw std::runtime_error("Unknown planner '" + name + "'.");
    }
}

}
}\
"""

def parse_version(version):
    return tuple(int(x) for x in version.split('.'))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--include-dirs', type=str,
                        help='OMPL include directories')
    args = parser.parse_args()

    include_dirs = args.include_dirs.split(os.path.pathsep)

    # Filter planners by version number.
    planners = yaml.load(sys.stdin)
    supported_planners = []

    for planner in planners:
        for include_dir in include_dirs:
            header_path = os.path.join(include_dir, planner['header'])
            if os.path.exists(header_path):
                supported_planners.append(planner)
                break

    planners = supported_planners

    # Include the necessary OMPL 
    headers = [ planner['header'] for planner in planners ]
    includes = [ '#include <{:s}>'.format(path) for path in headers ]
    print(factory_frontmatter.format(includes='\n'.join(includes)))

    # Generate the factory class implementations.
    names = [ planner['name'] for planner in planners ]
    registry_entries = []

    for qualified_name in names:
        _, _, name = qualified_name.rpartition('::')
        args = { 'name': name,
                 'qualified_name': qualified_name }
        print(factory_template.format(**args))
        registry_entries.append(registry_entry.format(**args))

    # Generate the registry of factory classes.
    print(registry_frontmatter)
    print('\n'.join(registry_entries))
    print(registry_backmatter)


if __name__ == '__main__':
    main()
