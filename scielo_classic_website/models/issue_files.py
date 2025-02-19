import glob
import logging
import os

from scielo_classic_website.htmlbody.html_body import HTMLFile
from scielo_classic_website.utils.files_utils import create_zip_file


def _get_classic_website_rel_path(file_path):
    for folder in (
        "bases",
        "htdocs",
    ):
        if folder in file_path:
            path = file_path[file_path.find(folder) + len(folder) :]
            return path


class IssueFiles:
    def __init__(self, acron, issue_folder, classic_website_paths):
        self.acron = acron
        self.issue_folder = issue_folder
        self._subdir_acron_issue = os.path.join(acron, issue_folder)
        self._htdocs_img_revistas_files = None
        self._bases_translation_files = None
        self._bases_pdf_files = None
        self._bases_xml_files = None
        self._classic_website_paths = classic_website_paths

    @property
    def files(self):
        if self.bases_xml_files:
            yield from self.bases_xml_files
        if self.bases_translation_files:
            yield from self.bases_translation_files
        if self.bases_pdf_files:
            yield from self.bases_pdf_files
        if self.htdocs_img_revistas_files:
            yield from self.htdocs_img_revistas_files

    @property
    def bases_translation_files(self):
        """
        Obtém os arquivos HTML de bases/translation/acron/volnum
        E os agrupa pelo nome do arquivo e idioma

        Returns
        -------
        dict which keys: paths, info
        "paths": [
            "/path/bases/translations/acron/volnum/pt_a01.htm",
            "/path/bases/translations/acron/volnum/pt_ba01.htm",
        ]
        "info": {
            "a01": {
                "pt": {"before": "pt_a01.htm",
                       "after": "pt_ba01.htm"}
            }
        }
        """
        if self._bases_translation_files is None:
            paths = glob.glob(
                os.path.join(
                    self._classic_website_paths.bases_translation_path,
                    self._subdir_acron_issue,
                    "*",
                )
            )
            files = []
            for path in paths:
                basename = os.path.basename(path)
                name, ext = os.path.splitext(basename)
                lang = name[:2]
                name = name[3:]
                label = "before"
                if name[0] == "b":
                    name = name[1:]
                    label = "after"
                files.append(
                    {
                        "type": "html",
                        "key": name,
                        "path": path,
                        "name": basename,
                        "relative_path": _get_classic_website_rel_path(path),
                        "lang": lang,
                        "part": label,
                        "replacements": HTMLFile(path).asset_path_fixes,
                    }
                )
            self._bases_translation_files = files
        return self._bases_translation_files

    @property
    def bases_pdf_files(self):
        """
        Obtém os arquivos PDF de bases/pdf/acron/volnum
        E os agrupa pelo nome do arquivo e idioma

        Returns
        -------
        dict which keys: zip_file_path, files
        "files":
            {"a01":
                    {"pt": "a01.pdf",
                     "en": "en_a01.pdf",
                     "es": "es_a01.pdf"}
            }
        """
        if self._bases_pdf_files is None:
            paths = glob.glob(
                os.path.join(
                    self._classic_website_paths.bases_pdf_path,
                    self._subdir_acron_issue,
                    "*",
                )
            )
            files = []
            for path in paths:
                basename = os.path.basename(path)
                name, ext = os.path.splitext(basename)
                if name[2] == "_":
                    # translations
                    lang = name[:2]
                    name = name[3:]
                else:
                    # main pdf
                    lang = None
                files.append(
                    {
                        "type": "pdf",
                        "key": name,
                        "path": path,
                        "name": basename,
                        "relative_path": _get_classic_website_rel_path(path),
                        "lang": lang,
                    }
                )
            self._bases_pdf_files = files
        return self._bases_pdf_files

    @property
    def htdocs_img_revistas_files(self):
        """
        Obtém os arquivos de imagens e outros de
        htdocs/img/revistas/acron/volnum/*
        htdocs/img/revistas/acron/volnum/*/*

        Returns
        -------
        dict
            zip_file_path
            files (original paths):
                {
                    path_completo_original: basename,
                    path_completo_original: basename,
                    path_completo_original: basename,
                    path_completo_original: basename,
                }
        """
        if self._htdocs_img_revistas_files is None:
            paths = glob.glob(
                os.path.join(
                    self._classic_website_paths.htdocs_img_revistas_path,
                    self._subdir_acron_issue,
                    "*",
                )
            )
            files = []
            for path in paths:
                if os.path.isfile(path):
                    files.append(
                        {
                            "type": "asset",
                            "path": path,
                            "relative_path": _get_classic_website_rel_path(path),
                            "name": os.path.basename(path),
                        }
                    )
                elif os.path.isdir(path):
                    for item in glob.glob(os.path.join(path, "*")):
                        files.append(
                            {
                                "type": "asset",
                                "path": item,
                                "relative_path": _get_classic_website_rel_path(item),
                                "name": os.path.basename(item),
                            }
                        )
            self._htdocs_img_revistas_files = files
        return self._htdocs_img_revistas_files

    @property
    def bases_xml_files(self):
        if self._bases_xml_files is None:
            paths = glob.glob(
                os.path.join(
                    self._classic_website_paths.bases_xml_path,
                    self._subdir_acron_issue,
                    "*.xml",
                )
            )
            files = []
            for path in paths:
                basename = os.path.basename(path)
                name, ext = os.path.splitext(basename)
                files.append(
                    {
                        "type": "xml",
                        "key": name,
                        "path": path,
                        "name": basename,
                        "relative_path": _get_classic_website_rel_path(path),
                    }
                )
            self._bases_xml_files = files
        return self._bases_xml_files


class ArtigoDBPath:
    def __init__(self, classic_website_paths, journal_acron, issue_folder):
        self.classic_website_paths = classic_website_paths
        self.journal_acron = journal_acron
        self.issue_folder = issue_folder

    def get_artigo_db_path(self):
        # ordem de preferencia para obter os arquivos de base de dados isis
        # que contém registros dos artigos
        callables = (
            self.get_db_from_serial_base_xml_dir,
            self.get_db_from_bases_work_acron_id,
            self.get_db_from_serial_base_dir,
            self.get_db_from_bases_work_acron_subset,
            self.get_db_from_bases_work_acron,
        )
        for func in callables:
            try:
                files = func()
                if files:
                    return files
            except Exception as e:
                logging.exception(e)
                continue
        return []

    def get_db_from_serial_base_xml_dir(self):
        items = []
        _serial_path = os.path.join(
            self.classic_website_paths.serial_path,
            self.journal_acron,
            self.issue_folder,
            "base_xml",
            "id",
        )

        if os.path.isdir(_serial_path):
            items.append(os.path.join(_serial_path, "i.id"))
            for item in os.listdir(_serial_path):
                if item != "i.id" and item.endswith(".id"):
                    items.append(os.path.join(_serial_path, item))
        return items

    def get_db_from_serial_base_dir(self):
        items = []
        _serial_path = os.path.join(
            self.classic_website_paths.serial_path,
            self.journal_acron,
            self.issue_folder,
            "base",
        )

        if os.path.isdir(_serial_path):
            items.append(os.path.join(_serial_path, self.issue_folder))
        return items

    def get_db_from_bases_work_acron_id(self):
        items = []
        _bases_work_acron_path = os.path.join(
            self.classic_website_paths.bases_work_path,
            self.journal_acron,
            self.journal_acron,
        )
        if os.path.isfile(_bases_work_acron_path + ".id"):
            items.append(_bases_work_acron_path + ".id")
        return items

    def get_db_from_bases_work_acron(self):
        items = []
        _bases_work_acron_path = os.path.join(
            self.classic_website_paths.bases_work_path,
            self.journal_acron,
            self.journal_acron,
        )
        items.append(_bases_work_acron_path)
        return items

    def get_db_from_bases_work_acron_subset(self):
        items = []
        _bases_work_acron_path = os.path.join(
            self.classic_website_paths.bases_work_path,
            self.journal_acron,
            self.journal_acron,
        )
        try:
            items.append(
                controller.isis_cmd.get_documents_by_issue_folder(
                    self.classic_website_paths.cisis_path,
                    _bases_work_acron_path,
                    self.issue_folder,
                )
            )
        except Exception as e:
            logging.exception(e)
        return items
