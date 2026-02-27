export type Pair = { pdf: string; txt: string; filename: string };
export type DoneDate = { key: string; label: string; count: number };
export type Step23State = "idle" | "running" | "done";
export type Settings = { grader_name: string; pdfxchange_path: string };

declare global {
  interface Window {
    pywebview: {
      api: {
        open_file_dialog: () => Promise<string | null>;
        open_output_dir: () => Promise<boolean>;
        open_with_pdfxchange: () => Promise<boolean>;
        extract_zip: (path: string) => Promise<boolean>;
        run_step1: () => Promise<boolean>;
        copy_pdf: (path: string) => Promise<boolean>;
        get_pairs: () => Promise<Pair[]>;
        get_done_dates: () => Promise<DoneDate[]>;
        restore_from_done: (date_str: string) => Promise<boolean>;
        get_pdf_image: (
          path: string,
          page: number,
          zoom: number
        ) => Promise<
          | { image_data: string; current_page: number; total_pages: number }
          | { error: string }
        >;
        read_text: (path: string) => Promise<string>;
        save_text: (path: string, content: string) => Promise<boolean>;
        run_step23: () => Promise<boolean>;
        get_settings: () => Promise<Settings>;
        save_settings: (
          grader_name: string,
          pdfxchange_path: string
        ) => Promise<boolean>;
        run_coordinate_picker: () => Promise<boolean>;
        cancel_step1: () => Promise<boolean>;
        cancel_step23: () => Promise<boolean>;
      };
    };
  }
}