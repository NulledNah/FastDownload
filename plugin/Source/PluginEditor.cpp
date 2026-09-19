#include "PluginEditor.h"

namespace
{
    const juce::String baseUrl = "http://127.0.0.1:" + juce::String (8731) + "/";

    // Registro: percorso del motore scritto dall'installer.
    juce::String engineFromRegistry()
    {
        for (auto* root : { "HKEY_CURRENT_USER", "HKEY_LOCAL_MACHINE" })
        {
            auto path = juce::WindowsRegistry::getValue (
                juce::String (root) + "\\Software\\FastDownload\\EnginePath", {});
            if (path.isNotEmpty()
                && juce::File (path).getChildFile ("server.py").existsAsFile())
                return path;
        }
        return {};
    }

    // Cartella del motore Python: installata, nel registro, o risalendo dall'eseguibile.
    juce::String engineHome()
    {
        auto ok = [] (const juce::String& p)
        {
            return p.isNotEmpty() && juce::File (p).getChildFile ("server.py").existsAsFile();
        };

        if (ok (FD_HOME))
            return juce::String (FD_HOME);

        auto fromReg = engineFromRegistry();
        if (ok (fromReg))
            return fromReg;

        auto dir = juce::File::getSpecialLocation (juce::File::currentExecutableFile)
                       .getParentDirectory();
        for (int i = 0; i < 10 && dir.exists(); ++i)
        {
            auto direct = dir.getFullPathName();
            if (ok (direct))
                return direct;
            auto nested = dir.getChildFile ("engine").getFullPathName();
            if (ok (nested))
                return nested;
            dir = dir.getParentDirectory();
        }

        return juce::String (FD_HOME);
    }
}

FastDownloadEditor::FastDownloadEditor (FastDownloadProcessor& p)
    : AudioProcessorEditor (&p), proc (p)
{
    addAndMakeVisible (status);
    status.setJustificationType (juce::Justification::centred);
    status.setColour (juce::Label::textColourId, juce::Colours::floralwhite);
    status.setText ("Starting FastDownload...", juce::dontSendNotification);

    juce::WebBrowserComponent::Options options;
    options = options
        .withBackend (juce::WebBrowserComponent::Options::Backend::webview2)
        .withKeepPageLoadedWhenBrowserIsHidden()
        .withWinWebView2Options (
            juce::WebBrowserComponent::Options::WinWebView2{}
                .withStatusBarDisabled()
                .withBuiltInErrorPageDisabled()
                .withBackgroundColour (juce::Colour (0xfff5ead6))
                .withUserDataFolder (juce::File::getSpecialLocation (
                    juce::File::tempDirectory).getChildFile ("FastDownloadWebView2")));

    browser = std::make_unique<juce::WebBrowserComponent> (options);
    addAndMakeVisible (*browser);

    setResizable (true, true);
    setResizeLimits (720, 480, 4096, 2160);
    setSize (1120, 740);

    if (serverUp())
    {
        browser->goToURL (baseUrl);
        status.setVisible (false);
        loaded = true;
    }
    else
    {
        launchServer();
        startTimer (250);
    }
}

FastDownloadEditor::~FastDownloadEditor()
{
    stopTimer();
    if (startedServer)
        server.kill();
}

bool FastDownloadEditor::serverUp()
{
    juce::StreamingSocket socket;
    return socket.connect ("127.0.0.1", kPort, 300);
}

void FastDownloadEditor::launchServer()
{
    const juce::String home = engineHome();
    const juce::String script = home + "/server.py";
    const juce::String port = juce::String (kPort);

    for (auto* exe : { "pythonw.exe", "python.exe" })
    {
        const juce::String command = juce::String (exe) + " \"" + script + "\" --port " + port;
        if (server.start (command))
        {
            startedServer = true;
            return;
        }
    }

    status.setText ("Python not found: run server.py manually.", juce::dontSendNotification);
}

void FastDownloadEditor::timerCallback()
{
    waitedMs += 250;

    if (serverUp())
    {
        stopTimer();
        browser->goToURL (baseUrl);
        status.setVisible (false);
        loaded = true;
        return;
    }

    if (waitedMs >= 15000)
    {
        stopTimer();
        status.setText ("FastDownload did not start: run server.py.", juce::dontSendNotification);
    }
}

void FastDownloadEditor::paint (juce::Graphics& g)
{
    g.fillAll (juce::Colour (0xfff5ead6));
}

void FastDownloadEditor::resized()
{
    const auto area = getLocalBounds();
    browser->setBounds (area);
    status.setBounds (area);
}
