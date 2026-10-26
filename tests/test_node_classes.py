import pandas as pd
import pytest
from musa.node_classes import classify_nodes, DEFAULT_POLICY


def test_classes_do_not_convert_rank_to_geology():
    data = pd.DataFrame({'interaction_orders': ['1-2', '1-2,1-3', '1-2'],
                         'order_status': ['known', 'known', 'ambiguous_classification'],
                         'source_layer': ['structural_candidates', 'potential_relations', 'structural_candidates'],
                         'score': [0., 100., 100.]})
    result = classify_nodes(data)
    assert result.node_class.tolist() == ['1-2', 'multiple_pairs', 'ambiguous_classification']
    assert result.node_weight.iloc[0] == 1
    assert result.node_weight.iloc[1:].isna().all()
    assert result.structural_trap_class.isna().all()
    assert result.score.equals(data.score)
    assert result.node_kind.iloc[1] == 'proximity'


def test_invalid_weights_rejected():
    with pytest.raises(ValueError):
        classify_nodes(pd.DataFrame(), {**DEFAULT_POLICY, 'weights': {'1-2': -1}})
