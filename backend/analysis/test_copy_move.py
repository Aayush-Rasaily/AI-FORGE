from backend.analysis.copy_move import detect_copy_move

if __name__ == "__main__":
    image_path = "C:\\Users\\Dell\\Desktop\\AI-FORGE\\data\\temp\\uploads\\0bb6e663-e23b-44b6-877c-fb902fe20a8c.webp"
    try:
        result = detect_copy_move(image_path)
        print("\n==============================")
        print("Copy-Move Detection Result")
        print("==============================")
        print(result)
    except Exception as e:
        print("Test skipped:", e)