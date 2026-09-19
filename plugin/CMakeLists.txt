cmake_minimum_required(VERSION 3.22)
project(FastDownload VERSION 1.0.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Pacchetto NuGet Microsoft.Web.WebView2 scaricato in external/webview2.
set(JUCE_WEBVIEW2_PACKAGE_LOCATION "${CMAKE_CURRENT_SOURCE_DIR}/external/webview2"
    CACHE PATH "WebView2 package location")

add_subdirectory(external/JUCE)

juce_add_plugin(FastDownload
    COMPANY_NAME "FastDownload"
    PLUGIN_MANUFACTURER_CODE Fdwn
    PLUGIN_CODE Fd01
    FORMATS VST3 Standalone
    IS_SYNTH FALSE
    NEEDS_MIDI_INPUT FALSE
    NEEDS_MIDI_OUTPUT FALSE
    IS_MIDI_EFFECT FALSE
    EDITOR_WANTS_KEYBOARD_FOCUS TRUE
    COPY_PLUGIN_AFTER_BUILD FALSE
    VST3_CATEGORIES "Fx"
    NEEDS_WEB_BROWSER TRUE
    NEEDS_WEBVIEW2 TRUE)

# Cartella del motore FastDownload (server.py + ui/), passata al plugin.
get_filename_component(FD_HOME "${CMAKE_CURRENT_SOURCE_DIR}/../engine" ABSOLUTE)
file(TO_CMAKE_PATH "${FD_HOME}" FD_HOME)

target_sources(FastDownload PRIVATE
    Source/PluginProcessor.cpp
    Source/PluginEditor.cpp)

target_compile_definitions(FastDownload PUBLIC
    JUCE_WEB_BROWSER=1
    JUCE_USE_WIN_WEBVIEW2=1
    JUCE_USE_WIN_WEBVIEW2_WITH_STATIC_LINKING=1
    JUCE_DISPLAY_SPLASH_SCREEN=0
    JUCE_VST3_CAN_REPLACE_VST2=0
    FD_HOME="${FD_HOME}")

target_link_libraries(FastDownload
    PRIVATE
        juce::juce_audio_processors
        juce::juce_audio_utils
        juce::juce_audio_devices
        juce::juce_gui_extra
    PUBLIC
        juce::juce_recommended_config_flags
        juce::juce_recommended_warning_flags)
