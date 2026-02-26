TEXFILES := $(wildcard *.tex)
SVGFILES := $(patsubst %.tex,../assets/%.svg,$(TEXFILES))

all: $(SVGFILES)

../assets/%.svg: %.tex
	@mkdir -p ../assets
	pdflatex -interaction=nonstopmode -output-directory=/tmp $<
	inkscape /tmp/$*.pdf --export-type=svg --export-filename=$@
	@rm -f /tmp/$*.pdf /tmp/$*.aux /tmp/$*.log

clean:
	rm -f ../assets/*.svg

.PHONY: all clean
