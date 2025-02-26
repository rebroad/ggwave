# CMakeLists.txt for ggwave-large-message example
# This example doesn't require building, as it's a Python script

# Install the Python script
install(
    FILES
        ggwave_large_message.py
    DESTINATION
        ${CMAKE_INSTALL_BINDIR}
    PERMISSIONS
        OWNER_READ OWNER_WRITE OWNER_EXECUTE
        GROUP_READ GROUP_EXECUTE
        WORLD_READ WORLD_EXECUTE
)