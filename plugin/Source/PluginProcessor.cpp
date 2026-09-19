#include "PluginProcessor.h"
#include "PluginEditor.h"

FastDownloadProcessor::FastDownloadProcessor()
    : AudioProcessor (BusesProperties()
                          .withInput  ("Input",  juce::AudioChannelSet::stereo(), true)
                          .withOutput ("Output", juce::AudioChannelSet::stereo(), true))
{
}

juce::AudioProcessorEditor* FastDownloadProcessor::createEditor()
{
    return new FastDownloadEditor (*this);
}

juce::AudioProcessor* JUCE_CALLTYPE createPluginFilter()
{
    return new FastDownloadProcessor();
}
