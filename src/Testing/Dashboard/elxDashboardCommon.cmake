# elastix Common Dashboard Script
#
# This script is shared among most elastix dashboard client machines.
# It contains basic dashboard driver code common to all clients.
#
# Checkout the directory containing this script to a path such as
# "/.../Dashboards/ctest-scripts/".  Create a file next to this
# script, say 'my_dashboard.cmake', with code of the following form:
#
#   # Client maintainer: someone@users.sourceforge.net
#   set(CTEST_SITE "machine.site")
#   set(CTEST_BUILD_NAME "Platform-Compiler")
#   set(CTEST_BUILD_CONFIGURATION Debug)
#   set(CTEST_CMAKE_GENERATOR "Unix Makefiles")
#   include(${CTEST_SCRIPT_DIRECTORY}/elx_dashboard_common.cmake)
#
# Then run a scheduled task (cron job) with a command line such as
#
#   ctest -S /.../Dashboards/ctest-scripts/my_dashboard.cmake -V
#
# By default the source and build trees will be placed in the path
# "/.../Dashboards/MyTests/".
#
# The following variables may be set before including this script
# to configure it:
#
#   dashboard_model       = Nightly | Experimental | Continuous
#   dashboard_cache       = Initial CMakeCache.txt file content
#   dashboard_url         = Subversion url to checkout
#   dashboard_do_coverage = True to enable coverage (ex: gcov)
#   dashboard_do_memcheck = True to enable memcheck (ex: valgrind)
#   CTEST_UPDATE_COMMAND  = path to svn command-line client
#   CTEST_BUILD_FLAGS     = build tool arguments (ex: -j2)
#   CTEST_DASHBOARD_ROOT  = Where to put source and build trees
#
# Note: this script is based on the vxl_common.cmake script.
#

cmake_minimum_required( VERSION 2.8 )

set( CTEST_PROJECT_NAME elastix )

# Select the top dashboard directory.
if( NOT DEFINED CTEST_DASHBOARD_ROOT )
  get_filename_component( CTEST_DASHBOARD_ROOT
    "${CTEST_SCRIPT_DIRECTORY}/../MyTests" ABSOLUTE )
endif()

# Select the model (Nightly, Experimental, Continuous).
if( NOT DEFINED dashboard_model )
  set( dashboard_model Nightly )
endif()

# Default to a Release build.
if( NOT DEFINED CTEST_BUILD_CONFIGURATION )
  set( CTEST_BUILD_CONFIGURATION Release )
endif()

# Select svn source to use.
if( NOT DEFINED dashboard_url )
  set( dashboard_url "https://svn.bigr.nl/elastix/trunkpublic" )
endif()

# Select a source directory name.
if( NOT DEFINED CTEST_SOURCE_DIRECTORY )
  set( CTEST_SOURCE_DIRECTORY "${CTEST_DASHBOARD_ROOT}/src" )
endif()

# Select a build directory name.
if( NOT DEFINED CTEST_BINARY_DIRECTORY )
  set( CTEST_BINARY_DIRECTORY ${CTEST_DASHBOARD_ROOT}/bin )
endif()
make_directory( ${CTEST_BINARY_DIRECTORY} )

# Look for a Subversion command-line client.
if( NOT DEFINED CTEST_UPDATE_COMMAND )
  find_program( CTEST_UPDATE_COMMAND svn
    HINTS "C:/cygwin/bin/" )
endif()

# Support initial checkout if necessary;
# dashboard_root is working dir.
if( NOT EXISTS "${CTEST_SOURCE_DIRECTORY}"
    AND NOT DEFINED CTEST_CHECKOUT_COMMAND
    AND CTEST_UPDATE_COMMAND)
  set( CTEST_CHECKOUT_COMMAND "\"${CTEST_UPDATE_COMMAND}\" co --username elastixguest --password elastixguest \"${dashboard_url}\" ." )
endif()

# Also check the dox directory for updates, not only the src directory.
SET( CTEST_EXTRA_UPDATES_1 "${CTEST_DASHBOARD_ROOT}/dox" )

# Send the main script as a note, and this script
list( APPEND CTEST_NOTES_FILES
  "${CTEST_SCRIPT_DIRECTORY}/${CTEST_SCRIPT_NAME}"
  "${CMAKE_CURRENT_LIST_FILE}" )

# Check for required variables.
foreach( req
  CTEST_CMAKE_GENERATOR
  CTEST_SITE
  CTEST_BUILD_NAME
  )
  if( NOT DEFINED ${req} )
    message( FATAL_ERROR "The containing script must set ${req}" )
  endif()
endforeach()

# Print summary information.
foreach( v
  CTEST_SITE
  CTEST_BUILD_NAME
  CTEST_SOURCE_DIRECTORY
  CTEST_BINARY_DIRECTORY
  CTEST_CMAKE_GENERATOR
  CTEST_BUILD_CONFIGURATION
  CTEST_UPDATE_COMMAND
  CTEST_CHECKOUT_COMMAND
  CTEST_SCRIPT_DIRECTORY
  dashboard_model
  )
  set( vars "${vars}  ${v}=[${${v}}]\n" )
endforeach()
message( "Configuration:\n${vars}\n" )

# Avoid non-ascii characters in tool output.
set( ENV{LC_ALL} C )

# Helper macro to write the initial cache.
macro( write_cache )
  if( CTEST_CMAKE_GENERATOR MATCHES "Make" )
    set( cache_build_type CMAKE_BUILD_TYPE:STRING=${CTEST_BUILD_CONFIGURATION} )
  endif()
  file( WRITE ${CTEST_BINARY_DIRECTORY}/CMakeCache.txt "
SITE:STRING=${CTEST_SITE}
BUILDNAME:STRING=${CTEST_BUILD_NAME}
${cache_build_type}
${dashboard_cache}
")
endmacro()

# Start with a fresh build tree.
message( "Clearing build tree..." )
ctest_empty_binary_directory( ${CTEST_BINARY_DIRECTORY} )

# Support each testing model
if( dashboard_model STREQUAL Continuous )
  # Build once and then when updates are found.
  while( ${CTEST_ELAPSED_TIME} LESS 43200 )
    set( START_TIME ${CTEST_ELAPSED_TIME} )
    ctest_start( Continuous )

    # always build if the tree is missing
    if( NOT EXISTS "${CTEST_BINARY_DIRECTORY}/CMakeCache.txt" )
      message( "Starting fresh build..." )
      write_cache()
      set( res 1 )
    endif()

    ctest_update( RETURN_VALUE res )
    message( "Found ${res} changed files" )
    if( res GREATER 0 )
      # run cmake twice; this seems to be necessary, otherwise the
      # KNN lib is not built
      ctest_configure()
      ctest_configure()
      ctest_read_custom_files( ${CTEST_BINARY_DIRECTORY} )
      ctest_build()
      ctest_test()
      ctest_submit()
    endif()

    # Delay until at least 10 minutes past START_TIME
    ctest_sleep( ${START_TIME} 600 ${CTEST_ELAPSED_TIME} )
  endwhile()
else()
  write_cache()
  ctest_start( ${dashboard_model} )
  ctest_update()
  # run cmake twice; this seems to be necessary, otherwise the
  # KNN lib is not built
  ctest_configure()
  ctest_configure()
  ctest_read_custom_files( ${CTEST_BINARY_DIRECTORY} )
  ctest_build()
  ctest_test()
  if( dashboard_do_coverage )
    ctest_coverage()
  endif()
  if( dashboard_do_memcheck )
    ctest_memcheck()
  endif()
  ctest_submit()
endif()

