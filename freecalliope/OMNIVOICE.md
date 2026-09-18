# OmniVoice Provider

OmniVoice is the project you meant by "omini voice": an open-source multilingual zero-shot TTS and voice-cloning model from `k2-fsa`.

Useful links:

- Official repo: https://github.com/k2-fsa/OmniVoice
- Demo/site: https://omnivoice.app/
- Colab notebook: https://colab.research.google.com/github/k2-fsa/OmniVoice/blob/master/docs/OmniVoice.ipynb
- Paper: https://arxiv.org/abs/2604.00688

## How FreeCalliope Uses OmniVoice

OmniVoice is a heavier voice model, so FreeCalliope treats it as an external Colab voice step:

1. Let FreeCalliope create the script and scenes.
2. Generate the narration audio with OmniVoice in Colab.
3. Set `VOICE_PROVIDER = "omnivoice"` in the FreeCalliope notebook.
4. Set `OMNIVOICE_AUDIO_PATH` to the generated OmniVoice `.wav` or `.mp3`.
5. Run FreeCalliope to render the final MP4 with that OmniVoice audio.

Example:

```python
VOICE_PROVIDER = "omnivoice"
OMNIVOICE_AUDIO_PATH = "/content/omnivoice_output.wav"
```

FreeCalliope copies the file into the project, converts WAV to MP3 when needed, and uses it for `videos/final.mp4`.
