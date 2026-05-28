all: compile

compile:
	mkdir -p build
	latexmk -pdf -outdir=build main.tex
	cp build/main.pdf SMDE_A1.pdf

clean:
	rm -rf build
