import plumber
from lxml import etree as ET

from scielo_migration.spsxml.sps_xml_attributes import (
    CONTRIB_ROLES,
    get_attribute_value,
)


class XMLArticleMetaSciELOArticleIdPipe(plumber.Pipe):

    def transform(self, data):
        raw, xml = data

        article_meta = xml.find('./front/article-meta')

        article_id_items = [
            {"value": raw.scielo_pid_v1, "pub-id-type": "publisher-id",
             "specific-use": "scielo-v1"},
            {"value": raw.scielo_pid_v2, "pub-id-type": "publisher-id",
             "specific-use": "scielo-v2"},
            {"value": raw.scielo_pid_v3, "pub-id-type": "publisher-id",
             "specific-use": "scielo-v3"},
            {"value": raw.aop_pid, "specific-use": "previous-pid"},
            {"value": raw.internal_sequence_id, "pub-id-type": "other"},
        ]

        for item in article_id_items:
            value = item.get("value")
            if value:
                article_id = ET.Element('article-id')
                for attr_name in ("pub-id-type", "specific-use"):
                    attr_value = item.get(attr_name)
                    if attr_value:
                        article_id.set(attr_name, attr_value)

                article_id.text = value
                article_meta.append(article_id)
        return data


class XMLArticleMetaArticleIdDOIPipe(plumber.Pipe):

    def precond(data):
        raw, xml = data

        if not raw.doi:
            raise plumber.UnmetPrecondition()

    @plumber.precondition(precond)
    def transform(self, data):
        raw, xml = data

        article_id = ET.Element('article-id')
        article_id.set('pub-id-type', 'doi')
        article_id.text = raw.doi

        xml.find('./front/article-meta').append(article_id)

        return data


class XMLArticleMetaArticleCategoriesPipe(plumber.Pipe):
    def precond(data):
        raw, xml = data
        if not raw.original_section:
            raise plumber.UnmetPrecondition()

    @plumber.precondition(precond)
    def transform(self, data):
        raw, xml = data

        subject_group = ET.Element('subj-group')
        subject_group.set('subj-group-type', 'heading')

        subject = ET.Element('subject')
        subject.text = raw.original_section

        subject_group.append(subject)

        article_categories = ET.Element('article-categories')
        article_categories.append(subject_group)

        xml.find('./front/article-meta').append(article_categories)

        return data


class XMLArticleMetaTitleGroupPipe(plumber.Pipe):

    def transform(self, data):
        raw, xml = data

        article_title = ET.Element('article-title')
        article_title.text = raw.original_title

        titlegroup = ET.Element('title-group')
        titlegroup.append(article_title)

        xml.find('./front/article-meta').append(titlegroup)

        return data


class XMLArticleMetaTranslatedTitleGroupPipe(plumber.Pipe):

    def precond(data):
        raw, xml = data
        if not raw.translated_titles:
            raise plumber.UnmetPrecondition()

    @plumber.precondition(precond)
    def transform(self, data):
        raw, xml = data

        for item in raw.translated_titles:
            trans_title = ET.Element('trans-title')
            trans_title.text = item["text"]

            trans_titlegrp = ET.Element('trans-title-group')
            trans_titlegrp.set('{http://www.w3.org/XML/1998/namespace}lang', item["language"])
            trans_titlegrp.append(trans_title)

            xml.find('./front/article-meta/title-group').append(trans_titlegrp)

        return data


class XMLArticleMetaContribGroupPipe(plumber.Pipe):

    def precond(data):

        raw, xml = data

        if not raw.authors:
            raise plumber.UnmetPrecondition()

    @plumber.precondition(precond)
    def transform(self, data):
        raw, xml = data

        contrib_group = ET.Element('contrib-group')
        for author in raw.authors:
            contrib_name = ET.Element('name')

            # cria os elementos surname e given-names em name
            for tag, attr_name in zip(("surname", "given-names"), ("surname", "given_names")):
                value = author.get(attr_name)
                if value:
                    elem = ET.Element(tag)
                    elem.text = value
                    contrib_name.append(elem)

            # cria o elemento contrib e seu atributo contrib-type
            contrib = ET.Element('contrib')
            try:
                contrib_type = CONTRIB_ROLES.get_sps_value(author["role"])
            except KeyError:
                contrib_type = "author"
            contrib.set('contrib-type', contrib_type)

            # contrib-id (lattes e orcid)
            for _contrib_id_type in ("lattes", "orcid"):
                try:
                    _contrib_id_value = author[_contrib_id_type]
                except KeyError:
                    continue
                else:
                    contrib_id = ET.Element('contrib-id')
                    contrib_id.set("contrib-id-type", _contrib_id_type)
                    contrib_id.text = _contrib_id_value
                    contrib.append(contrib_id)

            # inclui name como filho de contrib
            contrib.append(contrib_name)

            # crie os xref de contrib
            for xref_rid in author.get('xref', '').split(" "):
                if xref_rid:
                    xref = ET.Element('xref')
                    xref.set('ref-type', 'aff')
                    xref.set('rid', xref_rid)
                    contrib.append(xref)

            contrib_group.append(contrib)

        xml.find('./front/article-meta').append(contrib_group)

        return data


class XMLArticleMetaAffiliationPipe(plumber.Pipe):

    def precond(data):

        raw, xml = data

        if not raw.mixed_affiliations:
            raise plumber.UnmetPrecondition()

    @plumber.precondition(precond)
    def transform(self, data):
        raw, xml = data

        for affiliation in raw.affiliations:

            aff = ET.Element('aff')
            try:
                aff.set('id', affiliation['id'])
            except KeyError:
                pass

            addrline = None
            for tag in ("city", "state"):
                try:
                    value = affiliation[tag]
                except KeyError:
                    pass
                else:
                    elem = ET.Element('named-content')
                    elem.set('content-type', tag)
                    elem.text = value
                    if not addrline:
                        addrline = ET.Element('addr-line')
                    addrline.append(elem)

            attribs = ("orgname", "div", "div1", "div2", "div3")
            content_types = ("orgname", "orgdiv1", "orgdiv1", "orgdiv2", "orgdiv3")
            for attr, content_type in zip(attribs, content_types):
                try:
                    value = affiliation[attr]
                except KeyError:
                    pass
                else:
                    elem = ET.Element('institution')
                    elem.set('content-type', content_type)
                    elem.text = value
                    aff.append(elem)

            try:
                country = affiliation['country']
            except KeyError:
                pass
            else:
                country = get_attribute_value("country", country)
                if country:
                    elem = ET.Element('country')
                    elem.text = country['name']
                    elem.set('country', country['code'])
                    aff.append(country)

            try:
                value = affiliation['email']
            except KeyError:
                pass
            else:
                elem = ET.Element('email')
                elem.text = value
                aff.append(elem)

            xml.find('./front/article-meta').append(aff)

        return data
