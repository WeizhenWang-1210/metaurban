"""

RenderPipeline

Copyright (c) 2014-2016 tobspr <tobias.springer1@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

"""

from direct.stdpy.file import open

from metaurban.render_pipeline.rpcore.render_stage import RenderStage
from metaurban.render_pipeline.rpcore.globals import Globals


class UpdatePreviousPipesStage(RenderStage):
    """ This stage is constructed by the StageManager and stores all the
    current pipes in the previous pipe storage.

    This stage is a bit special, and not like the other stages, it does not
    specify inputs, since the StageManager passes all required inputs on demand.
    Also this stage does not load any shaders, but creates them on the fly.
    """
    def __init__(self, pipeline):
        RenderStage.__init__(self, pipeline)
        self._transfers = []

    def add_transfer(self, from_tex, to_tex):
        """ Adds a new texture which should be copied from "from_tex" to
        "to_tex". This should be called before the stage gets constructed.
        The source texture is expected to have the same size as the render
        resolution. """
        self._transfers.append((from_tex, to_tex))

    def create(self):
        self.debug("Creating previous pipes stage ..")
        self._target = self.create_target("StorePreviousPipes")
        self._target.prepare_buffer()

        # Set inputs
        for i, (from_tex, to_tex) in enumerate(self._transfers):  # pylint: disable=unused-variable
            self._target.set_shader_input("SrcTex" + str(i), from_tex)
            self._target.set_shader_input("DestTex" + str(i), to_tex)

    def set_dimensions(self):
        """ Sets the dimensions on all targets. See RenderTarget::set_dimensions """
        for from_tex, to_tex in self._transfers:  # pylint: disable=unused-variable
            to_tex.set_x_size(Globals.resolution.x)
            to_tex.set_y_size(Globals.resolution.y)

    def reload_shaders(self):
        """ This method augo-generates a shader which copies all textures specified
        as "from-tex" to the textures specified as "to-tex". """
        uniforms = []
        lines = []

        # Collect all samplers and generate the required uniforms and copy code
        for i, (from_tex, to_tex) in enumerate(self._transfers):
            index = str(i)
            uniforms.append(self.get_sampler_type(from_tex) + " SrcTex" + index)
            uniforms.append(self.get_sampler_type(to_tex, True) + " DestTex" + index)
            lines += [
                "\n  // Copying " + from_tex.get_name() + " to " + to_tex.get_name(),
                self.get_sampler_lookup(from_tex, "data" + index, "SrcTex" + index, "coord_2d_int"),
                self.get_store_code(to_tex, "DestTex" + index, "coord_2d_int", "data" + index),
                "\n",
            ]

        # Actually create the shader
        fragment = "#version 430\n"
        fragment += "\n// Autogenerated, do not edit! Your changes will be lost.\n\n"
        for uniform in uniforms:
            fragment += "uniform " + uniform + ";\n"
        fragment += "\nvoid main() {\n"
        fragment += "  ivec2 coord_2d_int = ivec2(gl_FragCoord.xy);\n"
        for line in lines:
            fragment += "  " + line + "\n"
        fragment += "}\n"

        # Write the shader
        shader_dest = "/$$rptemp/$$update_previous_pipes.frag.glsl"
        with open(shader_dest, "w") as handle:
            handle.write(fragment)

        # Load it back again
        self._target.shader = self.load_shader(shader_dest)

    def get_sampler_type(self, tex, can_write=False):  # pylint: disable=unused-argument
        """ Returns the matching GLSL sampler type for a Texture, or image type
        in case write access is required """
        # TODO: Add more sampler types based on texture type
        if not can_write:
            return "sampler2D"
        else:
            return "writeonly image2D"

    def get_sampler_lookup(self, tex, dest_name, sampler_name, coord_var):  # noqa # pylint: disable=unused-argument
        """ Returns the matching GLSL sampler lookup for a texture, storing the
        result in the given glsl variable """
        # TODO: Add more lookups based on texture type
        return "vec4 " + dest_name + " = texelFetch(" + sampler_name + ", " + coord_var + ", 0);"

    def get_store_code(self, tex, sampler_name, coord_var, data_var):  # noqa# pylint: disable=unused-argument
        """ Returns the matching GLSL code to store the given data in a given
        texture """
        # TODO: Add more stores based on texture type
        return "imageStore(" + sampler_name + ", " + coord_var + ", vec4(" + data_var + "));"
