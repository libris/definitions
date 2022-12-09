<!--
Example use:
$ curl -sL "https://raw.githubusercontent.com/unicode-org/cldr/main/common/bcp47/transform.xml" | xsltproc scripts/transformrule2kbv.xslt - 2>/dev/null | rdfpipe -ixml -ottl -

Caution! Resulting data falls under the "Unicode License Agreement - Data Files and Software":
    <https://www.unicode.org/license.txt> = <https://spdx.org/licenses/Unicode-DFS-2016.html>
which requires inclusion of this notice in resulting data and/or documentation!

So *if* we include this, we must link to that at least from id.kb.se docs!
-->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns="https://id.kb.se/vocab/">
    <xsl:param name="base">https://id.kb.se/i18n/bcp47/transform/m0/</xsl:param>
    <xsl:output method="xml" indent="yes" encoding="utf-8"/>
    <xsl:template match="/ldmlBCP47">
        <rdf:RDF>
            <xsl:apply-templates select="keyword/key[@extension='t']"/>
        </rdf:RDF>
    </xsl:template>
    <xsl:template match="key[@extension='t']/type">
        <LanguageTransformRules rdf:about="{$base}{@name}">
            <xsl:for-each select="@alias">
                <sameAs rdf:resource="{.}"/>
            </xsl:for-each>
            <code><xsl:value-of select="@name"/></code>
            <comment xml:lang="en"><xsl:value-of select="@description"/></comment>
        </LanguageTransformRules>
    </xsl:template>
</xsl:stylesheet>
