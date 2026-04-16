import argparse
from pathlib import Path

import torch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True, help="Path to .pt/.pth checkpoint")
    args = parser.parse_args()

    ckpt_path = Path(args.checkpoint)
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {ckpt_path}")

    ckpt = torch.load(ckpt_path, map_location="cpu")

    print("=" * 80)
    print(f"Checkpoint: {ckpt_path}")
    print(f"Python type: {type(ckpt)}")
    print("=" * 80)

    if isinstance(ckpt, dict):
        print("Top-level keys:")
        for k in ckpt.keys():
            print(f" - {k}")

        state_dict = None
        if "state_dict" in ckpt:
            state_dict = ckpt["state_dict"]
            print("\nUsing key: state_dict")
        elif "model_state_dict" in ckpt:
            state_dict = ckpt["model_state_dict"]
            print("\nUsing key: model_state_dict")
        else:
            # thử xem checkpoint chính là state_dict
            tensor_like = all(hasattr(v, "shape") for v in ckpt.values())
            if tensor_like:
                state_dict = ckpt
                print("\nCheckpoint appears to be a raw state_dict")

        if state_dict is not None:
            print("\nFirst 20 state_dict keys:")
            for i, key in enumerate(state_dict.keys()):
                if i >= 20:
                    break
                shape = tuple(state_dict[key].shape)
                print(f" - {key}: {shape}")

            # thử suy ra kiến trúc
            try:
                seq_input_dim = state_dict["lstm.weight_ih_l0"].shape[1]
                lstm_hidden = state_dict["lstm.weight_ih_l0"].shape[0] // 4
                node_input_dim = state_dict["node_proj.weight"].shape[1]
                gnn_hidden = state_dict["node_proj.weight"].shape[0]
                mlp_hidden = state_dict["mlp.0.weight"].shape[0]
                print("\nInferred model dims:")
                print(f" - seq_input_dim = {seq_input_dim}")
                print(f" - node_input_dim = {node_input_dim}")
                print(f" - lstm_hidden = {lstm_hidden}")
                print(f" - gnn_hidden = {gnn_hidden}")
                print(f" - mlp_hidden = {mlp_hidden}")
            except Exception as e:
                print(f"\nCould not infer model dims automatically: {e}")
        else:
            print("\nCould not find state_dict/model_state_dict in checkpoint.")
    else:
        print("Checkpoint is not a dict, inspect manually.")


if __name__ == "__main__":
    main()