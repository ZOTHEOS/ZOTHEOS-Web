"""Postimplementation adversarial supplement, separate from37prebuild proofs."""
import importlib.util
import os
from pathlib import Path

import pytest
from test_context_layer_sources import Context,fixture_data,public_model,write_data

if os.environ.get('ZOTHEOS_CONTEXT_MODULE'):
    spec=importlib.util.spec_from_file_location('context_control_check',Path(os.environ['ZOTHEOS_CONTEXT_MODULE']))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    Context=module.Context


@pytest.mark.parametrize('control',['\x00','\x01','\x7f'])
def test_literal_control_characters_cannot_be_approved_into_a_layer_url(tmp_path,control):
    doc,allow=fixture_data();url='https://alpha.example/'+control+'history'
    doc['public_notes'][0]['source_urls']=[url]
    doc['official_resources'][0]['url']=url;allow['links'][0]['url']=url
    write_data(tmp_path,doc,allow)
    with pytest.raises(ValueError):Context(tmp_path,public_model())
