#pragma once

#include <juce_gui_extra/juce_gui_extra.h>

#include "PluginProcessor.h"

/** Editor del plugin: ospita la UI di FastDownload in una WebView2.

    All'apertura avvia (se non già attivo) il motore Python `server.py`, che
    serve la UI e scarica i WAV in <cartella progetto FL>/FastDownload.
*/
class FastDownloadEditor : public juce::AudioProcessorEditor,
                           private juce::Timer
{
public:
    explicit FastDownloadEditor (FastDownloadProcessor&);
    ~FastDownloadEditor() override;

    void paint (juce::Graphics&) override;
    void resized() override;

private:
    void timerCallback() override;
    void launchServer();
    static bool serverUp();

    static constexpr int kPort = 8731;

    FastDownloadProcessor& proc;
    juce::ChildProcess server;
    bool startedServer = false;
    bool loaded = false;
    int  waitedMs = 0;

    std::unique_ptr<juce::WebBrowserComponent> browser;
    juce::Label status;

    JUCE_DECLARE_NON_COPYABLE_WITH_LEAK_DETECTOR (FastDownloadEditor)
};
